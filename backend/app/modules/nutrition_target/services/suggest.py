"""LLM-backed nutrition-target suggestion: TDEE + goal + conditions → macros.

Lives with the domain that owns the shape, not with an agent, because *both* agents
need it — the setup chatbot's `set_nutrition_target` tool and the meal-plan
`/suggest-setup` endpoint. Putting it here keeps agents from importing each other.

Has a deterministic fallback so a model outage never blocks a suggestion.
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from pydantic import BaseModel

from app.core.llm import structured

logger = logging.getLogger(__name__)


MACRO_SYSTEM = """You are a nutrition assistant. Given a user's estimated daily energy needs (TDEE),
their goal and health conditions, return a daily nutrition target (calories + protein/carb/fat grams).
Adjust calories for the goal (lose: deficit ~15-20%, gain: surplus ~10-15%, maintain: ~TDEE) and
choose a sensible macro split, respecting conditions (e.g. diabetes -> lower carbs, higher fiber/protein)."""


class SuggestedNutritionTarget(BaseModel):
    calories_kcal: int
    protein_g: float
    carbs_g: float
    fat_g: float
    rationale: str = ""


# Atwater factors: the energy the macros actually carry.
KCAL_PER_G_PROTEIN = 4
KCAL_PER_G_CARB = 4
KCAL_PER_G_FAT = 9

# How far the macros may drift from the calorie figure before we stop trusting them.
# Rounding to whole grams across three macros is worth a percent or two; 8% is slack
# for that and nothing more.
MACRO_CONSISTENCY_TOLERANCE = 0.08


def macro_kcal(protein_g: float, carbs_g: float, fat_g: float) -> float:
    return (protein_g * KCAL_PER_G_PROTEIN + carbs_g * KCAL_PER_G_CARB
            + fat_g * KCAL_PER_G_FAT)


def _split_macros(calories: int) -> tuple[float, float, float]:
    """30/40/30 protein/carb/fat by ENERGY — consistent with `calories` by construction."""
    return (round(calories * 0.30 / KCAL_PER_G_PROTEIN, 1),
            round(calories * 0.40 / KCAL_PER_G_CARB, 1),
            round(calories * 0.30 / KCAL_PER_G_FAT, 1))


def _goal_adjusted_calories(tdee: int, goal_type: Optional[str]) -> int:
    if goal_type == "lose":
        return int(tdee * 0.82)
    if goal_type == "gain":
        return int(tdee * 1.12)
    return tdee


def suggest_nutrition_target(tdee: int, goal_type: Optional[str], conditions: list,
                             notes: Optional[str]) -> SuggestedNutritionTarget:
    user_msg = json.dumps({
        "tdee_kcal": tdee, "goal_type": goal_type,
        "health_conditions": conditions, "notes": notes,
    })
    try:
        out = structured(SuggestedNutritionTarget).invoke(
            [("system", MACRO_SYSTEM), ("human", user_msg)]
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("macro suggestion LLM failed, using deterministic fallback: %s", e)
        cal = _goal_adjusted_calories(tdee, goal_type)
        p, c, f = _split_macros(cal)
        return SuggestedNutritionTarget(calories_kcal=cal, protein_g=p, carbs_g=c, fat_g=f,
                                        rationale="deterministic fallback")

    # The schema bounds each field but cannot see that they must add up. Observed in
    # production: 2640 kcal alongside 120P/108C/48F, which is 1344 kcal — the user was
    # shown a target that under-feeds them by half. Calories are the number the plan is
    # built on, so keep them and rebuild the macros rather than dropping the suggestion.
    implied = macro_kcal(out.protein_g, out.carbs_g, out.fat_g)
    if out.calories_kcal <= 0 or abs(implied - out.calories_kcal) > (
            MACRO_CONSISTENCY_TOLERANCE * out.calories_kcal):
        logger.warning("macro suggestion inconsistent (%d kcal declared, %.0f from macros) "
                       "— rebuilding split", out.calories_kcal, implied)
        cal = out.calories_kcal if out.calories_kcal > 0 else _goal_adjusted_calories(tdee, goal_type)
        p, c, f = _split_macros(cal)
        return SuggestedNutritionTarget(
            calories_kcal=cal, protein_g=p, carbs_g=c, fat_g=f,
            rationale=(out.rationale or "") + " (macros rebuilt to match calories)",
        )
    return out
