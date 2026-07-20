"""LLM-backed meal-structure suggestion: profile → how the day's meals split.

Lives with the domain that owns the shape rather than with an agent, for the same
reason as `nutrition_target/services/suggest.py`: both agents consume it, and agents
must not import each other.

Has a deterministic fallback so a model outage never blocks a suggestion.
"""
from __future__ import annotations

import json
import logging

from pydantic import BaseModel

from app.core.llm import structured

logger = logging.getLogger(__name__)


STRUCTURE_SYSTEM = """You are a nutrition assistant. Suggest a daily meal structure (how many timed
meals and their names/times) for the user, given their profile. meal_time MUST be exactly one of
breakfast/lunch/dinner/snack (use 'snack' for any extra eating occasion); calories_pct sum to 100."""


class SuggestedSlot(BaseModel):
    meal_time: str
    name: str
    calories_pct: float


class SuggestedMealStructure(BaseModel):
    timed_meals_per_day: int
    slots: list[SuggestedSlot]


# The default split, used when the model is unavailable.
_DEFAULT_SLOTS = [
    ("breakfast", "Breakfast", 25.0),
    ("lunch", "Lunch", 35.0),
    ("dinner", "Dinner", 30.0),
    ("snack", "Snack", 10.0),
]


def default_meal_structure() -> SuggestedMealStructure:
    return SuggestedMealStructure(
        timed_meals_per_day=len(_DEFAULT_SLOTS),
        slots=[SuggestedSlot(meal_time=mt, name=n, calories_pct=p) for mt, n, p in _DEFAULT_SLOTS],
    )


def suggest_meal_structure(profile: dict) -> SuggestedMealStructure:
    try:
        return structured(SuggestedMealStructure).invoke(
            [("system", STRUCTURE_SYSTEM), ("human", json.dumps(profile, default=str))]
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("structure suggestion LLM failed, using deterministic fallback: %s", e)
        return default_meal_structure()
