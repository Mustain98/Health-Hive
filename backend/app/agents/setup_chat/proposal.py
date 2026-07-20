"""Validation for the plan changes the agent proposes.

The contract that makes the chat honest: **validation happens before the user is asked,
not after they approve.** An item the risk guard would refuse never reaches the approval
card — `validate_items` raises `ItemError` carrying the violated bound and the safe
values, so the model corrects itself in the same turn. The user is never offered a
choice the system intends to refuse.

Each validated item carries the equivalent write-tool call (`tool` + `args`), so applying
an approved item is just invoking that tool from the normal registry.

Staging used to live here too — a `plan_proposals` table that persisted a batch between
the proposal and the user's decision. LangGraph's checkpointer now holds the suspended
run (see `hitl.py`), so that layer was redundant and is gone.
"""
from __future__ import annotations

import uuid
from typing import Any, Callable, Optional

from sqlmodel import Session, select

from app.modules.daily_goal.models import DailyGoal
from app.modules.daily_goal.schemas import (
    DailyGoalType, normalize_days_of_week, validate_daily_goal_attributes,
    validate_unit_for_type,
)
from app.modules.daily_goal.services import risk as dg_risk
from app.modules.milestone.models import Milestone
from app.modules.milestone.schemas import (
    GoalType, MilestoneType, MilestoneUnit, goal_type_for_milestone,
    validate_milestone_attributes,
)
from app.modules.milestone.services import risk as milestone_risk
from app.modules.nutrition_target.services.suggest import macro_kcal
from app.modules.user.models import UserData

# What a proposal item may describe, and which write tool applies it.
_TOOL_FOR = {
    ("milestone", "set"): "set_milestone",
    ("milestone", "delete"): "delete_milestone",
    ("daily_goal", "set"): "add_daily_goal",
    ("daily_goal", "delete"): "delete_daily_goal",
    ("nutrition_target", "set"): "set_nutrition_target",
    ("nutrition_target", "delete"): "delete_nutrition_target",
    ("meal_setting", "set"): "set_meal_setting",
    ("meal_setting", "delete"): "delete_meal_setting",
}

KINDS = sorted({k for k, _ in _TOOL_FOR})

# Deletes cannot be edited into something else — only approved or rejected.
_DELETE_DECISIONS = ["approve", "reject"]
_SET_DECISIONS = ["approve", "edit", "reject"]

# Nutrition: how far the macros may drift from the calorie figure. Matches the
# tolerance the suggestion service repairs at, so the two cannot disagree.
_MACRO_TOLERANCE = 0.08


class ItemError(ValueError):
    """An item that must not be shown to the user. Carries the model's remedy."""

    def __init__(self, reason: str, **hints: Any) -> None:
        super().__init__(reason)
        self.reason = reason
        self.hints = hints


# ── Validation ─────────────────────────────────────────────────────────────

def _user_data(session: Session, user_id: uuid.UUID) -> Optional[UserData]:
    return session.exec(select(UserData).where(UserData.user_id == user_id)).first()


def _validate_milestone(session: Session, user_id: uuid.UUID, item: dict) -> tuple[dict, str, str]:
    raw_type = item.get("milestone_type")
    try:
        mtype = MilestoneType(raw_type) if raw_type else None
    except ValueError:
        raise ItemError(f"invalid milestone_type {raw_type!r}",
                        allowed=[m.value for m in MilestoneType])
    if mtype is None:
        raise ItemError("milestone_type is required", allowed=[m.value for m in MilestoneType])

    unit = item.get("unit")
    if unit is not None:
        try:
            MilestoneUnit(unit)
        except ValueError:
            raise ItemError(f"invalid unit {unit!r}", allowed=[u.value for u in MilestoneUnit])

    try:
        attrs = validate_milestone_attributes(mtype, item.get("attributes"))
    except ValueError as e:
        raise ItemError(f"invalid attributes: {e}")

    ud = _user_data(session, user_id)
    # A transient Milestone purely so the real guard judges the real shape. Never added
    # to the session — validation must not be able to write.
    probe = Milestone(
        created_for=user_id, created_by=user_id, active=False,
        goal_type=goal_type_for_milestone(mtype) or GoalType.maintain,
        milestone_type=mtype, name=item.get("name"),
        target_weight=item.get("target_weight"), target_value=item.get("target_value"),
        initial_weight=ud.weight_kg if ud else None,
        duration_days=item.get("duration_days"), attributes=attrs,
    )
    reason = milestone_risk.is_risky_milestone(session, user_id, probe)
    if reason:
        hints: dict[str, Any] = {}
        if ud and ud.height_cm and ud.weight_kg:
            hints["safe_bounds"] = milestone_risk.safe_bounds(ud.height_cm, ud.weight_kg)
            if probe.target_weight:
                days = milestone_risk.min_safe_duration_days(ud.weight_kg, probe.target_weight)
                if days:
                    hints["min_safe_duration_days_for_this_target"] = days
        raise ItemError(f"unsafe milestone: {reason}", **hints)

    args = {k: item.get(k) for k in
            ("milestone_type", "name", "target_weight", "target_value", "unit", "duration_days")
            if item.get(k) is not None}
    if attrs:
        args["attributes"] = attrs
    if item.get("milestone_id"):
        args["milestone_id"] = item["milestone_id"]

    label = item.get("name") or mtype.value.replace("_", " ")
    bits = []
    if item.get("target_weight"):
        bits.append(f"target {item['target_weight']} kg")
    if item.get("target_value"):
        bits.append(f"{item['target_value']} kg muscle")
    if item.get("duration_days"):
        weeks = round(item["duration_days"] / 7)
        bits.append(f"over {item['duration_days']} days (~{weeks} weeks)")
    if item.get("reasoning"):
        args["reasoning"] = item["reasoning"]
    return args, label, " · ".join(bits) or mtype.value.replace("_", " ")


def _validate_daily_goal(session: Session, user_id: uuid.UUID, item: dict) -> tuple[dict, str, str]:
    raw_type = item.get("goal_type")
    try:
        gtype = DailyGoalType(raw_type) if raw_type else None
    except ValueError:
        raise ItemError(f"invalid goal_type {raw_type!r}",
                        allowed=[g.value for g in DailyGoalType])
    if gtype is None:
        raise ItemError("goal_type is required", allowed=[g.value for g in DailyGoalType])
    if not (item.get("name") or "").strip():
        raise ItemError("name is required")

    unit = item.get("unit")
    if unit is not None:
        from app.modules.daily_goal.schemas.daily_goal import DailyGoalUnit
        try:
            enum_unit = DailyGoalUnit(unit)
            validate_unit_for_type(gtype, enum_unit)
        except ValueError as e:
            raise ItemError(str(e))
    try:
        attrs = validate_daily_goal_attributes(gtype, item.get("attributes"))
    except ValueError as e:
        raise ItemError(f"invalid attributes: {e}")

    days = normalize_days_of_week(item.get("days_of_week"))
    probe = DailyGoal(created_for=user_id, created_by=user_id, goal_type=gtype,
                      name=item["name"], target_value=item.get("target_value"),
                      unit=unit, active=False, days_of_week=days, attributes=attrs)
    reason = dg_risk.is_risky_daily_goal(session, user_id, probe)
    if reason:
        raise ItemError(f"unsafe daily goal: {reason}")

    args = {"name": item["name"], "goal_type": gtype.value}
    for k in ("target_value", "unit"):
        if item.get(k) is not None:
            args[k] = item[k]
    if days:
        args["days_of_week"] = days
    if attrs:
        args["attributes"] = attrs
    if item.get("daily_goal_id"):
        args["daily_goal_id"] = item["daily_goal_id"]

    if item.get("reasoning"):
        args["reasoning"] = item["reasoning"]

    detail = " ".join(str(x) for x in (item.get("target_value"), unit) if x) or gtype.value
    return args, item["name"], detail


def _validate_nutrition(session: Session, user_id: uuid.UUID, item: dict) -> tuple[dict, str, str]:
    cal = item.get("calories_kcal")
    p, c, f = item.get("protein_g"), item.get("carbs_g"), item.get("fat_g")
    if cal is None:
        # Deriving from the milestone + TDEE is the tool's job; nothing to check here.
        return ({"from_milestone": True}, "Nutrition target", "derived from your milestone")
    if not all(v is not None for v in (p, c, f)):
        raise ItemError("protein_g, carbs_g and fat_g are all required when calories_kcal is given")

    implied = macro_kcal(p, c, f)
    if abs(implied - cal) > _MACRO_TOLERANCE * cal:
        # The defect this catches: 2640 kcal proposed alongside macros worth 1344 kcal.
        raise ItemError(
            f"macros don't match calories: {p}P/{c}C/{f}F is {implied:.0f} kcal, "
            f"but calories_kcal says {cal}",
            fix="protein and carbs are 4 kcal/g, fat is 9 kcal/g — make them add up, or "
                "omit the macros entirely and let the tool derive them",
        )
    args = {"calories_kcal": cal, "protein_g": p, "carbs_g": c, "fat_g": f}
    if item.get("reasoning"):
        args["reasoning"] = item["reasoning"]
    return args, "Nutrition target", f"{cal} kcal · P{p} · C{c} · F{f}"


def _validate_meal_setting(session: Session, user_id: uuid.UUID, item: dict) -> tuple[dict, str, str]:
    slots = item.get("slots") or []
    if not slots:
        raise ItemError("at least one meal slot is required")
    args = {"slots": slots}
    if item.get("name"):
        args["name"] = item["name"]
    if item.get("setting_id"):
        args["setting_id"] = item["setting_id"]
    if item.get("reasoning"):
        args["reasoning"] = item["reasoning"]
    detail = " · ".join(f"{s.get('meal_time') or s.get('name')} {s.get('calories_pct')}%"
                        for s in slots)
    return args, item.get("name") or "Meal setting", detail


_VALIDATORS: dict[str, Callable[[Session, uuid.UUID, dict], tuple[dict, str, str]]] = {
    "milestone": _validate_milestone,
    "daily_goal": _validate_daily_goal,
    "nutrition_target": _validate_nutrition,
    "meal_setting": _validate_meal_setting,
}


def validate_items(session: Session, user_id: uuid.UUID, items: list[dict]) -> list[dict]:
    """Normalize a proposed batch into staged items, or raise ItemError for the batch.

    All-or-nothing on purpose: a partially staged batch would show the user a card that
    silently omits what they asked for.
    """
    if not items:
        raise ItemError("items is empty — propose at least one change")

    staged: list[dict] = []
    problems: list[dict] = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            problems.append({"index": i, "reason": "each item must be an object"})
            continue
        kind, op = item.get("kind"), (item.get("op") or "set")
        tool = _TOOL_FOR.get((kind, op))
        if not tool:
            problems.append({"index": i,
                             "reason": f"unknown kind/op {kind!r}/{op!r}",
                             "allowed_kinds": KINDS})
            continue
        if op == "delete":
            staged.append({"kind": kind, "op": op, "tool": tool,
                           "args": {k: v for k, v in item.items()
                                    if k.endswith("_id") and v is not None},
                           "label": item.get("name") or kind.replace("_", " "),
                           "detail": "will be removed",
                           "allowed": _DELETE_DECISIONS})
            continue
        try:
            args, label, detail = _VALIDATORS[kind](session, user_id, item)
        except ItemError as e:
            problems.append({"index": i, "name": item.get("name"),
                             "reason": e.reason, **e.hints})
            continue
        staged.append({"kind": kind, "op": op, "tool": tool, "args": args,
                       "label": label, "detail": detail, "allowed": _SET_DECISIONS})

    if problems:
        raise ItemError(
            "nothing was proposed — fix these items and call propose_plan_changes again",
            invalid=problems,
            how_to_fix="Correct the listed items NOW, in this same turn, using the safe "
                       "values provided. Do not tell the user to consult anyone unless "
                       "they insist on a target you have already shown is unsafe.",
        )
    return staged

