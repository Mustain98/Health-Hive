"""Meal-plan constraint generation.

A single-shot structured-output call — no tool loop, no middleware. The model only
*thinks*: it splits the daily macro target across slots and describes what each slot
should retrieve. Combo assembly and selection stay deterministic in `service.py`.

Every call has a deterministic fallback so generation never hard-fails.
"""
from __future__ import annotations

import json
import logging
from typing import List, Optional

from app.core.llm import structured
from app.agents.meal_plan.prompts import CONSTRAINT_SYSTEM
from app.agents.meal_plan.schemas import (
    MacroTarget, Composition, TimedMealConstraint, DayConstraintPlan,
)

logger = logging.getLogger(__name__)


def generate_constraints(
    profile: dict,
    macro_target: dict,
    slots: Optional[List[dict]] = None,
    allowed_labels: Optional[List[str]] = None,
) -> DayConstraintPlan:
    """slots: optional list of {meal_time, name, labels?, calories_pct?} from a MealPlanSetting.
    allowed_labels: the valid MealLabelName vocabulary the LLM may use for required/preferred_labels."""
    allowed = set(allowed_labels or [])
    user_msg = (
        f"User profile:\n{json.dumps(profile, default=str, indent=2)}\n\n"
        f"Daily macro target:\n{json.dumps(macro_target)}\n\n"
        f"ALLOWED LABELS (use only these for required_labels/preferred_labels):\n"
        f"{json.dumps(sorted(allowed))}\n\n"
        f"Meal structure (pinned by user; null = you decide):\n{json.dumps(slots, default=str)}\n\n"
        "Return one constraint per slot."
    )
    try:
        plan: DayConstraintPlan = structured(DayConstraintPlan).invoke(
            [("system", CONSTRAINT_SYSTEM), ("human", user_msg)]
        )
        if plan and plan.slots:
            if allowed:
                for s in plan.slots:  # strip any hallucinated labels
                    s.required_labels = [l for l in s.required_labels if l in allowed]
                    s.preferred_labels = [l for l in s.preferred_labels if l in allowed]
            return plan
    except Exception as e:  # noqa: BLE001
        logger.warning("constraint LLM failed, using deterministic fallback: %s", e)
    return fallback_constraints(macro_target, slots, profile)


def fallback_query(slot: dict, profile: Optional[dict]) -> str:
    """A descriptive-enough retrieval query when the LLM is unavailable."""
    meal_time = slot.get("meal_time") or "meal"
    name = slot.get("name") or meal_time.title()
    parts = [f"balanced home-style {meal_time} — {name}, moderate portion, whole foods"]
    if profile:
        diet = [str(d) for d in (profile.get("diet_preferences") or [])]
        conds = [str(c) for c in (profile.get("health_conditions") or [])]
        if diet:
            parts.append(", ".join(diet))
        if "hypertension" in conds:
            parts.append("low-sodium heart-healthy")
        if "diabetes" in conds:
            parts.append("high-fiber low-sugar diabetic-friendly")
    return ", ".join(parts)


def fallback_constraints(macro_target: dict, slots: Optional[List[dict]],
                         profile: Optional[dict] = None) -> DayConstraintPlan:
    if slots:
        base = slots
    else:
        # Same default split as meal_plan_setting.services.suggest.default_meal_structure.
        base = [
            {"meal_time": "breakfast", "name": "Breakfast", "calories_pct": 25},
            {"meal_time": "lunch", "name": "Lunch", "calories_pct": 35},
            {"meal_time": "dinner", "name": "Dinner", "calories_pct": 30},
            {"meal_time": "snack", "name": "Snack", "calories_pct": 10},
        ]
    n = len(base)
    out: List[TimedMealConstraint] = []
    for s in base:
        pct = s.get("calories_pct") or (100.0 / n)
        frac = pct / 100.0
        labels = s.get("labels") or ([s.get("meal_time")] if s.get("meal_time") else [])
        out.append(TimedMealConstraint(
            meal_time=s.get("meal_time", "lunch"),
            name=s.get("name", s.get("meal_time", "Meal").title()),
            macros=MacroTarget(
                calories=round(macro_target["calories"] * frac, 1),
                protein_g=round(macro_target["protein_g"] * frac, 1),
                carbs_g=round(macro_target["carbs_g"] * frac, 1),
                fat_g=round(macro_target["fat_g"] * frac, 1),
            ),
            composition=Composition(components=["main"], allow_dessert=False, max_items=2),
            required_labels=[l for l in labels if l],
            preferred_labels=[],
            retrieval_query=fallback_query(s, profile),
            rationale="deterministic fallback",
        ))
    return DayConstraintPlan(slots=out)
