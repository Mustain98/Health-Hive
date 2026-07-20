"""Setup-chatbot tools: JSON schemas (for bind_tools) + DB-backed implementations.

`build_tool_registry` returns a {name: callable} map whose functions close over the
request's DB session + user, so the generic tool loop in llm.py stays DB-agnostic.
Tools are called by the LLM ONLY when it needs the data — general chit-chat pulls no PII.
"""
from typing import Callable, Optional
import uuid

from fastapi import HTTPException
from sqlmodel import Session, select, delete

from app.modules.user.models import UserData, UserHealthProfile
from app.modules.milestone.models import Milestone
from app.modules.nutrition_target.models import NutritionTarget
from app.modules.meal_plan_setting.models import MealPlanSetting, MealPlanSettingTimedMeal
from app.agents.setup_chat.models import PlanSetupSession, PlanSetupMessage
from app.modules.daily_goal import services as dg_service
from app.modules.milestone.services import risk
from app.modules.milestone.services.suggest import propose_milestone as suggest_milestone
from app.modules.daily_goal.schemas import DailyGoalCreate, DailyGoalUpdate
from app.modules.milestone.schemas import GoalType, MilestoneType, goal_type_for_milestone, validate_milestone_attributes
from app.utils.calculate import calculate_tdee, calculate_bmi
from app.utils.text import short
from app.agents.setup_chat.proposal import validate_items, ItemError

from app.modules.nutrition_target.services.suggest import suggest_nutrition_target
from app.modules.daily_goal.schemas import validate_unit_for_type
from app.modules.milestone.schemas import MilestoneUnit
from app.modules.nutrition_target.schemas import (
    CALORIES_KCAL_MIN, CALORIES_KCAL_MAX, PROTEIN_G_MIN, PROTEIN_G_MAX,
    CARBS_G_MIN, CARBS_G_MAX, FAT_G_MIN, FAT_G_MAX,
)

# Bounds come from the nutrition_target schema so there is one source of truth —
# this table used to re-declare the same four ranges a third time.
_NT_BOUNDS = {
    "calories_kcal": (CALORIES_KCAL_MIN, CALORIES_KCAL_MAX),
    "protein_g": (PROTEIN_G_MIN, PROTEIN_G_MAX),
    "carbs_g": (CARBS_G_MIN, CARBS_G_MAX),
    "fat_g": (FAT_G_MIN, FAT_G_MAX),
}

# Habit-format rules, attached to the tools that need them rather than the system
# prompt, so the model reads them at the moment it makes the call.
_DAILY_GOAL_FORMAT = (
    "FORMAT RULES: one goal per habit. STRENGTH: one goal PER EXERCISE — name is the exercise "
    "('Back Squat'), goal_type=exercise, unit='sets', target_value=number of sets, reps go in "
    "attributes (never minutes when the user says sets/reps); a 'leg day with 5 exercises on "
    "Monday' is FIVE calls, each days_of_week=[0]. TIMED CARDIO/activity: unit='min' (or "
    "'steps'), target_value=duration/count. Never put a weekday in the name ('Treadmill', not "
    "'Treadmill Monday'). ROUTING: calories/protein/carb/fat intake are NOT daily goals — they "
    "belong to set_nutrition_target; daily goals are behaviours (exercises, steps, water in "
    "'glasses', sleep)."
)


def _clamp(name, v):
    lo, hi = _NT_BOUNDS[name]
    return max(lo, min(hi, v))


# ── Schemas advertised to the model (OpenAI function-calling format) ─────────
TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "get_health_data",
        "description": "Everything about the user for planning in one call: body metrics (age, gender, "
                       "height, weight, activity) + derived TDEE and BMI + diet preferences + health "
                       "conditions + notes. Call it whenever the chat is about the user's plan/health; "
                       "then analyze what's relevant and explain your rationale. Also returns "
                       "`safe_bounds` (healthy weight range for this height, max safe weekly change) "
                       "and two ready-made safe proposals, `suggested_milestone` and "
                       "`suggested_milestone_if_muscle_focused` — pick the one matching what the user "
                       "asked for and present ITS numbers. NEVER propose values outside safe_bounds.",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "get_current_setup",
        "description": "The user's currently ACTIVE milestone/goal, nutrition target and meal setting "
                       "(if any).",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "list_plans",
        "description": "List the user's plans (yours/AI/consultant) with each plan's id, parts and "
                       "which are active/missing. Use to view or target a specific plan or part by id.",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "continue_draft_plan",
        "description": "Point this chat at an EXISTING inactive draft plan (by id from list_plans) so "
                       "further edits build into it. Use when the user wants to keep working on a "
                       "specific earlier plan.",
        "parameters": {"type": "object", "properties": {"plan_id": {"type": "string"}},
                       "required": ["plan_id"]},
    }},
    {"type": "function", "function": {
        "name": "start_new_draft_plan",
        "description": "Begin a BRAND-NEW draft plan instead of adding to the current/latest one. Use "
                       "when the user explicitly wants a separate, different plan. Will return an error asking you to confirm with the user if an empty draft already exists, unless force_create is set.",
        "parameters": {"type": "object", "properties": {
            "force_create": {"type": "boolean", "description": "Set to true to skip the empty draft check if the user confirmed they want a new one despite having an empty draft."}
        }},
    }},
    {"type": "function", "function": {
        "name": "get_past_session_summaries",
        "description": "Short summaries of the user's previous setup chats. Call when the user refers "
                       "to something discussed before.",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "get_session_transcript",
        "description": "Full transcript of a specific past setup chat. Pass a session_id from "
                       "get_past_session_summaries (or omit to use the chat the user referenced).",
        "parameters": {"type": "object", "properties": {"session_id": {"type": "string"}}},
    }},
    # ── Batch Write Tool ──
    {"type": "function", "function": {
        "name": "propose_plan_changes",
        "description": "Propose one or more changes to the plan (milestone, daily goals, nutrition, meal setting). "
                       "Always use this tool to write or delete plan items. You can batch multiple items in one call. "
                       "For 'kind', use: 'milestone', 'daily_goal', 'nutrition_target', or 'meal_setting'. "
                       "For 'op', use: 'set' or 'delete'. " + _DAILY_GOAL_FORMAT,
        "parameters": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "kind": {"type": "string"},
                            "op": {"type": "string"},
                            "name": {"type": "string"},
                            "milestone_type": {"type": "string"},
                            "target_weight": {"type": "number"},
                            "target_value": {"type": "number"},
                            "unit": {"type": "string"},
                            "duration_days": {"type": "integer"},
                            "goal_type": {"type": "string"},
                            "days_of_week": {"type": "array", "items": {"type": "integer"}},
                            "attributes": {"type": "object"},
                            "calories_kcal": {"type": "integer"},
                            "protein_g": {"type": "number"},
                            "carbs_g": {"type": "number"},
                            "fat_g": {"type": "number"},
                            "slots": {
                                "type": "array", 
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "meal_time": {"type": "string", "description": "e.g., breakfast, lunch, dinner, snack"},
                                        "name": {"type": "string"},
                                        "calories_pct": {"type": "integer", "description": "Percentage of daily calories"},
                                        "protein_g_pct": {"type": "integer", "description": "Percentage of daily protein (default to calories_pct if uniform)"},
                                        "carbs_g_pct": {"type": "integer", "description": "Percentage of daily carbs (default to calories_pct if uniform)"},
                                        "fat_g_pct": {"type": "integer", "description": "Percentage of daily fat (default to calories_pct if uniform)"},
                                        "description": {"type": "string", "description": "Explain what this meal should contain"},
                                        "meal_labels": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                            "description": "Optional tags like halal, high_protein, low_carb, vegetarian, etc"
                                        }
                                    },
                                    "required": ["meal_time", "calories_pct", "description"]
                                }
                            },
                            "reasoning": {"type": "string", "description": "Explain why this change is being proposed"}
                        },
                        "required": ["kind", "op"]
                    }
                }
            },
            "required": ["items"]
        }
    }},

]


def _enum(v):
    return v.value if hasattr(v, "value") else v


def _fail(session, e) -> dict:
    """Report a tool failure AND clear the transaction.

    Without the rollback, a statement that failed mid-flush leaves the Session in a
    pending-rollback state: every later statement — including the chat's own transcript
    write at the end of the turn — raises PendingRollbackError. The user then loses the
    whole turn instead of just the failed write.
    """
    try:
        session.rollback()
    except Exception:  # noqa: BLE001
        pass
    from fastapi import HTTPException as _HTTPException
    return {"error": e.detail if isinstance(e, _HTTPException) else str(e)}


# ── Draft-plan choice: the picker the UI renders instead of a prose question ──
#
# When a write cannot proceed until the user picks a draft plan, the tool appends a
# CHOICE_KIND record to the caller's `signals` list. The service re-resolves that record
# against COMMITTED state at the end of the turn and emits it as a `choice` SSE frame.
#
# The signal is what makes this precise: the *condition* ("unpinned and drafts exist") is
# true on every turn of such a session, so emitting off the condition alone would pop the
# picker when the user merely says "hi". The signal records that a write was actually
# blocked; the re-resolve handles the snapshot going stale mid-turn.

CHOICE_KIND = "choose_draft_plan"

_CHOICE_HINT = (
    "The UI is now showing the user clickable plan cards. Reply with ONE short sentence "
    "asking them to pick one below. Do NOT call list_plans. Do NOT name, number, describe, "
    "enumerate or compare the plans, and NEVER write a plan id in your reply. Do not call "
    "any other tool this turn."
)


def _inactive_plans(session: Session, user_id: uuid.UUID) -> list:
    """The user's draft (inactive) plans, newest first — the picker's slots."""
    from app.modules.plan.models import Plan
    return list(session.exec(select(Plan).where(
        Plan.created_for == user_id, Plan.active == False)  # noqa: E712
        .order_by(Plan.created_at.desc())).all())


def pinned_draft_id(session: Session, setup_session_id) -> Optional[uuid.UUID]:
    """The session's draft pointer, or None when it is unset OR points at a plan that no
    longer exists / has since been activated.

    Hardened deliberately: reading `s.draft_plan_id` raw returned a stale id for a plan the
    user had activated in the meantime, which slipped past the guard and let the chat write
    into a LIVE plan.
    """
    from app.modules.plan.models import Plan
    if not setup_session_id:
        return None
    s = session.get(PlanSetupSession, setup_session_id)
    if not s or not s.draft_plan_id:
        return None
    p = session.get(Plan, s.draft_plan_id)
    if not p or p.active or p.created_for != s.user_id:
        return None
    return p.id


def draft_choice_signal(session: Session, user_id: uuid.UUID, setup_session_id,
                        *, reason: str) -> Optional[dict]:
    """The picker record when this chat must not write until the user picks a draft, else
    None. Deterministic and idempotent, so it is safe to re-evaluate at emit time.

    reason: "unpinned_with_drafts" — a write was attempted with no draft pinned.
            "empty_draft_exists"  — a new plan was requested while an empty draft is going spare.
    """
    # The submodule, not the package: `services/__init__` does `from .plan import *`, and a
    # star import skips underscore names — `services._parts` does not exist.
    from app.modules.plan.services import plan as plan_service
    pinned = pinned_draft_id(session, setup_session_id)

    if reason == "unpinned_with_drafts":
        if pinned:
            return None  # already pointed somewhere — nothing to ask
        plans = _inactive_plans(session, user_id)
        if not plans:
            return None  # nothing to reuse; the caller auto-creates as before
    elif reason == "empty_draft_exists":
        plans = _inactive_plans(session, user_id)
        if not any(not any(plan_service._parts(session, p.id)) for p in plans):
            return None  # no empty draft going spare — let the new plan be created
    else:
        return None

    return {
        "kind": CHOICE_KIND,
        "reason": reason,
        "plans": [plan_service.plan_dict(session, p) for p in plans],
        "allow_new": True,
        "pinned_at_signal": str(pinned or ""),
    }


def resolve_choice_signal(session: Session, user_id: uuid.UUID, setup_session_id,
                          signal: Optional[dict]) -> Optional[dict]:
    """Re-resolve a recorded signal against COMMITTED state, rebuilding `plans` from the DB.

    Returns the frame payload, or None when the choice no longer applies — the model may
    have resolved it itself mid-turn (e.g. it was refused, asked the user, and then called
    `start_new_draft_plan(force_create=true)`, which pins a plan). Showing a picker after
    that would be a dead control.
    """
    if not signal or signal.get("kind") != CHOICE_KIND:
        return None
    reason = signal.get("reason")
    if reason == "empty_draft_exists":
        # force_create ran and won: the session moved to a different plan since the refusal.
        if str(pinned_draft_id(session, setup_session_id) or "") != signal.get("pinned_at_signal", ""):
            return None
    return draft_choice_signal(session, user_id, setup_session_id, reason=reason)


def build_tool_registry(
    session: Session, user_id: uuid.UUID, reference_session_id: Optional[uuid.UUID] = None,
    setup_session_id: Optional[uuid.UUID] = None, *, signals: Optional[list] = None,
) -> dict[str, Callable]:
    """`signals` is a caller-owned list the draft-choice guards append to; the service reads
    it after the turn to decide whether to emit a `choice` frame. Keyword-only so existing
    positional callers keep working."""

    def _signal(rec: dict) -> None:
        if signals is not None:
            signals.append(rec)

    def get_health_data(**_):
        """Everything about the user for planning: body metrics + derived TDEE/BMI +
        diet preferences + health conditions + notes. The assistant decides which
        signals to use and must explain its rationale to the user."""
        ud = session.exec(select(UserData).where(UserData.user_id == user_id)).first()
        hp = session.get(UserHealthProfile, user_id)
        out = {
            "age": ud.age if ud else None, "gender": _enum(ud.gender) if ud else None,
            "height_cm": ud.height_cm if ud else None, "weight_kg": ud.weight_kg if ud else None,
            "activity_level": _enum(ud.activity_level) if ud else None,
            "diet_preferences": (hp.diet_preferences if hp else []) or [],
            "health_conditions": (hp.health_conditions if hp else []) or [],
            "notes": hp.notes if hp else None,
        }
        if ud and ud.height_cm and ud.weight_kg:
            out["bmi"] = calculate_bmi(ud.weight_kg, ud.height_cm)  # one signal among several
            # The envelope a proposal must stay inside, plus a ready-made proposal that
            # already sits in it. Without these the model guesses, the guard rejects, and
            # the chat degenerates into "please see a professional".
            out["safe_bounds"] = risk.safe_bounds(ud.height_cm, ud.weight_kg)
            # Two framings of the SAME safe trajectory — pick by what the user asked for.
            # Muscle framing does not mean a bigger target: muscle gain is bound by the
            # same weekly ceiling, it only changes the type and how it is described.
            out["suggested_milestone"] = suggest_milestone(ud.height_cm, ud.weight_kg)
            out["suggested_milestone_if_muscle_focused"] = suggest_milestone(
                ud.height_cm, ud.weight_kg, wants_muscle=True)
        if ud and all([ud.age, ud.gender, ud.height_cm, ud.weight_kg, ud.activity_level]):
            out["tdee_kcal"] = calculate_tdee(ud.age, _enum(ud.gender), ud.height_cm,
                                              ud.weight_kg, _enum(ud.activity_level))
        if not ud:
            out["note"] = "no body metrics on file — ask the user to fill their profile"
        return out

    def get_current_setup(**_):
        goal = session.exec(select(Milestone).where(
            Milestone.created_for == user_id, Milestone.active == True)).first()  # noqa: E712
        target = session.exec(select(NutritionTarget).where(
            NutritionTarget.created_for == user_id, NutritionTarget.active == True)).first()  # noqa: E712
        setting = session.exec(select(MealPlanSetting).where(
            MealPlanSetting.created_for == user_id, MealPlanSetting.active == True)).first()  # noqa: E712
        return {
            "milestone": None if not goal else {
                "milestone_type": _enum(goal.milestone_type), "name": goal.name,
                "goal_type": _enum(goal.goal_type), "target_weight": goal.target_weight,
                "target_value": goal.target_value, "unit": goal.unit, "duration_days": goal.duration_days},
            "nutrition_target": None if not target else {
                "calories_kcal": target.calories_kcal, "protein_g": target.protein_g,
                "carbs_g": target.carbs_g, "fat_g": target.fat_g},
            "meal_setting": None if not setting else {
                "name": setting.name, "timed_meals_per_day": setting.timed_meals_per_day},
        }

    def get_past_session_summaries(**_):
        rows = session.exec(
            select(PlanSetupSession)
            .where(PlanSetupSession.user_id == user_id, PlanSetupSession.summary.is_not(None))
            .order_by(PlanSetupSession.created_at.desc())
            .limit(5)
        ).all()
        return [{"session_id": str(r.id), "created_at": str(r.created_at), "summary": r.summary}
                for r in rows]

    def get_session_transcript(session_id: Optional[str] = None, **_):
        sid = session_id or (str(reference_session_id) if reference_session_id else None)
        if not sid:
            return {"error": "no session_id provided"}
        try:
            sid_uuid = uuid.UUID(sid)
        except (ValueError, TypeError):
            return {"error": "invalid session_id"}
        owner = session.get(PlanSetupSession, sid_uuid)
        if not owner or owner.user_id != user_id:
            return {"error": "session not found"}
        msgs = session.exec(
            select(PlanSetupMessage).where(PlanSetupMessage.session_id == sid_uuid)
            .order_by(PlanSetupMessage.created_at.asc())
        ).all()
        return [{"role": _enum(m.role), "content": m.content} for m in msgs]

    # ── Daily-goal action tools (reuse the service → validation + risk checks) ──
    def _dg_dict(dg):
        return {"id": str(dg.id), "name": dg.name, "goal_type": _enum(dg.goal_type),
                "target_value": dg.target_value, "unit": dg.unit, "active": dg.active,
                "days_of_week": dg.days_of_week, "attributes": dg.attributes}

    def list_daily_goals(**_):
        return [_dg_dict(g) for g in dg_service.list_daily_goals(session, user_id)]

    def add_daily_goal(name=None, goal_type=None, target_value=None, unit=None,
                       days_of_week=None, attributes=None, **_):
        try:
            # Upsert: same type + name = the same habit — update it, never stack a duplicate.
            # Scoped to THIS draft plan. A user-wide scan matched habits belonging to older
            # plans and updated them in place, leaving them on the old plan_id — so the goal
            # the user just asked for never joined the plan being built and looked unsaved.
            plan = _draft_plan()
            key = dg_service.dedup_key(goal_type, name)
            existing = next((g for g in dg_service.list_daily_goals(session, user_id)
                             if g.plan_id == plan.id
                             and dg_service.dedup_key(g.goal_type, g.name) == key), None)
            if existing:
                fields = {k: v for k, v in (("target_value", target_value), ("unit", unit),
                                            ("days_of_week", days_of_week), ("attributes", attributes))
                          if v is not None}
                dg = dg_service.update_daily_goal(session, user_id, existing.id, DailyGoalUpdate(**fields))
                return {"ok": True, "daily_goal": _dg_dict(dg),
                        "note": "existing goal updated (no duplicate created)"}
            dg = dg_service.create_daily_goal(session, user_id, DailyGoalCreate(
                goal_type=goal_type, name=name, target_value=target_value, unit=unit,
                days_of_week=days_of_week, attributes=attributes or {},
                active=False),  # inactive draft; user activates
                plan_id=plan.id)
            return {"ok": True, "daily_goal": _dg_dict(dg)}
        except (HTTPException, Exception) as e:  # noqa: BLE001
            return _fail(session, e)

    def update_daily_goal(daily_goal_id=None, **kwargs):
        fields = {k: kwargs[k] for k in ("name", "goal_type", "target_value", "unit",
                                         "days_of_week", "attributes")
                  if kwargs.get(k) is not None}
        try:
            dg = dg_service.update_daily_goal(
                session, user_id, uuid.UUID(str(daily_goal_id)), DailyGoalUpdate(**fields))
            return {"ok": True, "daily_goal": _dg_dict(dg)}
        except HTTPException as e:
            return _fail(session, e)
        except (ValueError, TypeError):
            return {"error": "invalid daily_goal_id"}

    def delete_daily_goal(daily_goal_id=None, **_):
        try:
            dg_service.delete_daily_goal(session, user_id, uuid.UUID(str(daily_goal_id)))
            return {"ok": True}
        except HTTPException as e:
            return _fail(session, e)
        except (ValueError, TypeError):
            return {"error": "invalid daily_goal_id"}

    # ── Plan-scoped DRAFT tools: parts attach to the draft Plan this chat builds ──
    def _setup_session():
        return session.get(PlanSetupSession, setup_session_id) if setup_session_id else None

    def _draft_plan():
        from app.modules.plan import services as plan_service
        return plan_service.get_or_create_session_draft_plan(session, user_id, _setup_session())

    def _active_milestone():
        return session.exec(select(Milestone).where(
            Milestone.created_for == user_id, Milestone.active == True)).first()  # noqa: E712

    def _draft_plan_id():  # the current draft plan's id WITHOUT creating one
        return pinned_draft_id(session, setup_session_id)

    def _milestone_of(plan_id):
        return session.exec(select(Milestone).where(Milestone.plan_id == plan_id)).first() if plan_id else None

    def _target_of(plan_id):
        return session.exec(select(NutritionTarget).where(NutritionTarget.plan_id == plan_id)).first() if plan_id else None

    def _setting_of(plan_id):
        return session.exec(select(MealPlanSetting).where(MealPlanSetting.plan_id == plan_id)).first() if plan_id else None

    def set_milestone(milestone_id=None, milestone_type=None, name=None, target_weight=None,
                      target_value=None, unit=None, duration_days=None, attributes=None, **_):
        if milestone_id:  # edit a specific existing milestone (active or consultant-made) in place
            g = session.get(Milestone, uuid.UUID(str(milestone_id)))
            if not g or g.created_for != user_id:
                return {"error": "milestone not found"}
        else:  # part of the draft plan
            plan = _draft_plan()
            g = _milestone_of(plan.id) or Milestone(created_for=user_id, created_by=user_id, active=False,
                                                   goal_type=GoalType.maintain, plan_id=plan.id)
        if milestone_type is not None:
            try:
                mt = MilestoneType(milestone_type)
            except ValueError:
                return {"error": f"invalid milestone_type {milestone_type}"}
            g.milestone_type = mt
            g.goal_type = goal_type_for_milestone(mt)
        if name is not None: g.name = short(name, 120)
        if target_weight is not None: g.target_weight = target_weight
        if target_value is not None: g.target_value = target_value
        if unit is not None:
            # Closed vocabulary — reject here with a clear message rather than
            # letting it fail later against the column's CHECK constraint.
            try:
                g.unit = MilestoneUnit(unit)
            except ValueError:
                return {"error": f"invalid unit '{unit}'. Allowed: "
                                 f"{[u.value for u in MilestoneUnit]}"}
        if duration_days is not None: g.duration_days = duration_days
        if attributes is not None:
            try:
                g.attributes = validate_milestone_attributes(g.milestone_type, attributes)
            except ValueError as e:
                return _fail(session, e)
        reason = risk.is_risky_milestone(session, user_id, g)
        if reason:
            # `g` may be a PERSISTENT row we just mutated in place (edit path). Returning
            # here without rolling back leaves those unsafe values dirty in the shared
            # session, and the next commit — another tool's, or the transcript write at
            # the end of the turn — flushes them. "not saved" has to be true.
            attempted_target = g.target_weight
            attempted_start = g.initial_weight
            session.rollback()
            err = {
                "error": f"unsafe milestone — NOT saved: {reason}",
                "how_to_fix": "Re-propose a corrected milestone NOW, in this same turn, using the "
                              "safe values below. Refer the user to a consultant only if they "
                              "insist on the unsafe target after seeing your safe alternative.",
            }
            ud = session.exec(select(UserData).where(UserData.user_id == user_id)).first()
            if ud and ud.height_cm and ud.weight_kg:
                err["safe_bounds"] = risk.safe_bounds(ud.height_cm, ud.weight_kg)
                if attempted_target:
                    days = risk.min_safe_duration_days(attempted_start or ud.weight_kg, attempted_target)
                    if days:
                        err["min_safe_duration_days_for_this_target"] = days
            return err
        session.add(g); session.commit(); session.refresh(g)
        return {"ok": True, "milestone": {"id": str(g.id), "milestone_type": _enum(g.milestone_type),
                "name": g.name, "target_weight": g.target_weight, "target_value": g.target_value,
                "unit": g.unit, "duration_days": g.duration_days, "active": g.active}}

    def delete_milestone(milestone_id=None, **_):
        g = session.get(Milestone, uuid.UUID(str(milestone_id))) if milestone_id else _milestone_of(_draft_plan_id())
        if not g or g.created_for != user_id:
            return {"error": "milestone not found"}
        from app.modules.milestone.models import MilestoneLog
        session.exec(delete(MilestoneLog).where(MilestoneLog.goal_id == g.id))
        session.delete(g); session.commit()
        return {"ok": True}

    def set_nutrition_target(target_id=None, calories_kcal=None, protein_g=None, carbs_g=None, fat_g=None,
                             from_milestone=False, **_):
        if from_milestone or calories_kcal is None:
            ud = session.exec(select(UserData).where(UserData.user_id == user_id)).first()
            if not ud or not all([ud.age, ud.gender, ud.height_cm, ud.weight_kg, ud.activity_level]):
                return {"error": "need body metrics (age/gender/height/weight/activity) to derive a target"}
            tdee = calculate_tdee(ud.age, _enum(ud.gender), ud.height_cm, ud.weight_kg, _enum(ud.activity_level))
            goal = _milestone_of(_draft_plan_id()) or _active_milestone()
            gt = _enum(goal.goal_type) if goal else None
            hp = session.get(UserHealthProfile, user_id)
            macro = suggest_nutrition_target(
                tdee, gt, hp.health_conditions if hp else [], hp.notes if hp else None)
            calories_kcal = calories_kcal if calories_kcal is not None else macro.calories_kcal
            protein_g = protein_g if protein_g is not None else macro.protein_g
            carbs_g = carbs_g if carbs_g is not None else macro.carbs_g
            fat_g = fat_g if fat_g is not None else macro.fat_g
        vals = {"calories_kcal": _clamp("calories_kcal", int(round(calories_kcal))),
                "protein_g": _clamp("protein_g", float(protein_g or 0)),
                "carbs_g": _clamp("carbs_g", float(carbs_g or 0)),
                "fat_g": _clamp("fat_g", float(fat_g or 0))}
        if target_id:  # edit a specific existing target in place
            t = session.get(NutritionTarget, uuid.UUID(str(target_id)))
            if not t or t.created_for != user_id:
                return {"error": "nutrition target not found"}
            for k, v in vals.items():
                setattr(t, k, v)
        else:
            plan = _draft_plan()
            t = _target_of(plan.id)
            if t is None:
                t = NutritionTarget(created_for=user_id, created_by=user_id, active=False, plan_id=plan.id, **vals)
            else:
                for k, v in vals.items():
                    setattr(t, k, v)
        session.add(t); session.commit(); session.refresh(t)
        return {"ok": True, "nutrition_target": {"id": str(t.id), **vals, "active": t.active}}

    def delete_nutrition_target(target_id=None, **_):
        t = session.get(NutritionTarget, uuid.UUID(str(target_id))) if target_id else _target_of(_draft_plan_id())
        if not t or t.created_for != user_id:
            return {"error": "nutrition target not found"}
        session.delete(t); session.commit()
        return {"ok": True}

    def set_meal_setting(setting_id=None, name=None, slots=None, **_):
        from app.agents.meal_plan.service import _coerce_meal_time
        if setting_id:  # edit a specific existing setting in place
            st = session.get(MealPlanSetting, uuid.UUID(str(setting_id)))
            if not st or st.created_for != user_id:
                return {"error": "meal setting not found"}
            if name is not None:
                st.name = short(name, 120)
        else:
            plan = _draft_plan()
            st = _setting_of(plan.id)
            if st is None:
                st = MealPlanSetting(created_for=user_id, created_by=user_id, active=False, plan_id=plan.id,
                                     name=short(name or "AI Draft Plan", 120), timed_meals_per_day=0)
                session.add(st); session.flush()
            elif name is not None:
                st.name = short(name, 120)
        if slots:
            from app.core.enums import MealLabelName
            total = sum((s.get("calories_pct") or 0) for s in slots) or 100.0
            session.exec(delete(MealPlanSettingTimedMeal).where(
                MealPlanSettingTimedMeal.meal_plan_setting_id == st.id))
            for s in slots:
                pct = round((s.get("calories_pct") or 0) * 100.0 / total, 1)
                valid_labels = [MealLabelName(lbl) for lbl in (s.get("meal_labels") or []) if lbl in [e.value for e in MealLabelName]]
                session.add(MealPlanSettingTimedMeal(
                    meal_plan_setting_id=st.id,
                    name=short(s.get("name") or s.get("meal_time") or "Meal", 100),
                    meal_time=_coerce_meal_time(s.get("meal_time")),
                    calories_pct=pct,
                    protein_g_pct=s.get("protein_g_pct", pct), carbs_g_pct=s.get("carbs_g_pct", pct),
                    fat_g_pct=s.get("fat_g_pct", pct), description=short(s.get("description"), 500),
                    meal_labels=valid_labels))
            st.timed_meals_per_day = len(slots)
        session.add(st); session.commit(); session.refresh(st)
        return {"ok": True, "meal_setting": {"id": str(st.id), "name": st.name,
                "timed_meals_per_day": st.timed_meals_per_day, "active": st.active}}

    def delete_meal_setting(setting_id=None, **_):
        st = session.get(MealPlanSetting, uuid.UUID(str(setting_id))) if setting_id else _setting_of(_draft_plan_id())
        if not st or st.created_for != user_id:
            return {"error": "meal setting not found"}
        session.exec(delete(MealPlanSettingTimedMeal).where(
            MealPlanSettingTimedMeal.meal_plan_setting_id == st.id))
        session.delete(st); session.commit()
        return {"ok": True}

    def list_plans_tool(**_):
        from app.modules.plan import services as plan_service
        return plan_service.list_plans(session, user_id)

    def continue_draft_plan(plan_id=None, **_):
        """Point this chat at an existing INACTIVE draft plan so further edits build into it."""
        from app.modules.plan import services as plan_service
        s = _setup_session()
        if not s:
            return {"error": "no active setup session"}
        try:
            p = plan_service.pin_session_draft_plan(session, user_id, s, uuid.UUID(str(plan_id)))
        except HTTPException as e:
            return _fail(session, e)
        except (ValueError, TypeError):
            return {"error": "invalid plan_id"}
        return {"ok": True, "plan": plan_service.plan_dict(session, p)}

    def start_new_draft_plan_tool(force_create=False, **_):
        """Begin a brand-new draft plan (don't add to the current/latest one)."""
        from app.modules.plan import services as plan_service
        s = _setup_session()
        if not s:
            return {"error": "no active setup session"}

        if not force_create:
            sig = draft_choice_signal(session, user_id, setup_session_id,
                                      reason="empty_draft_exists")
            if sig:
                _signal(sig)
                return {
                    "error": "The user already has an empty draft plan going spare, so they must "
                             "choose whether to reuse one or create another. If they say they want "
                             "a brand-new one anyway, call this tool again with force_create=true.",
                    "hint": _CHOICE_HINT,
                }

        p = plan_service.start_new_draft_plan(session, user_id, s)
        return {"ok": True, "plan": plan_service.plan_dict(session, p)}

    registry = {
        "get_health_data": get_health_data,
        "get_current_setup": get_current_setup,
        "list_plans": list_plans_tool,
        "continue_draft_plan": continue_draft_plan,
        "start_new_draft_plan": start_new_draft_plan_tool,
        "get_past_session_summaries": get_past_session_summaries,
        "get_session_transcript": get_session_transcript,
        "list_daily_goals": list_daily_goals,
        # Actually apply the items in propose_plan_changes
        # It's mapped here because proposal.py expects tool names.
        "set_milestone": set_milestone,
        "delete_milestone": delete_milestone,
        "add_daily_goal": add_daily_goal,
        "update_daily_goal": update_daily_goal,
        "delete_daily_goal": delete_daily_goal,
        "set_nutrition_target": set_nutrition_target,
        "delete_nutrition_target": delete_nutrition_target,
        "set_meal_setting": set_meal_setting,
        "delete_meal_setting": delete_meal_setting,
    }

    def propose_plan_changes(items=None, **_):
        if not items:
            return {"error": "items array is required"}

        # Enforce explicit draft selection if unpinned and drafts exist.
        sig = draft_choice_signal(session, user_id, setup_session_id,
                                  reason="unpinned_with_drafts")
        if sig:
            _signal(sig)
            return {
                "error": "This chat is not pointed at a draft plan yet, and the user has existing "
                         "drafts. Do not write anything until they pick one.",
                "hint": _CHOICE_HINT,
            }

        try:
            staged = validate_items(session, user_id, items)
        except ItemError as e:
            return {"error": e.reason, "hints": e.hints}
        
        results = []
        for item in staged:
            tool_name = item.get("tool")
            fn = registry.get(tool_name)
            if not fn:
                results.append({"error": f"Tool {tool_name} not found"})
                continue
            args = item.get("args") or {}
            try:
                res = fn(**args)
                results.append(res or {"ok": True})
            except Exception as ex:
                results.append({"error": str(ex)})
        return {"ok": True, "results": results}

    registry["propose_plan_changes"] = propose_plan_changes
    return registry
