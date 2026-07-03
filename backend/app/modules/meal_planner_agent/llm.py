"""LangChain (ChatGroq) reasoning layer for meal planning.

The LLM does the *thinking* only:
  - per-timed-meal constraint generation (macros + composition rules + labels + query)
  - setup suggestions (nutrition target, meal structure) via tool-callable chains
Combo assembly/selection is deterministic (see meal_plan_service).
Every call has a deterministic fallback so generation never hard-fails.
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import List, Optional

from pydantic import BaseModel, Field
from langchain_core.tools import tool

GROQ_MODEL = "llama-3.3-70b-versatile"


# ── Structured output schemas ──────────────────────────────────────────────

class MacroTarget(BaseModel):
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float


class Composition(BaseModel):
    components: List[str] = Field(description='e.g. ["main"] or ["main","side"]')
    allow_dessert: bool = False
    max_items: int = 2
    min_servings: float = 1.0
    max_servings: float = 3.0


class TimedMealConstraint(BaseModel):
    meal_time: str = Field(description="one of: breakfast, lunch, dinner, snack")
    name: str
    macros: MacroTarget
    composition: Composition
    required_labels: List[str] = []
    preferred_labels: List[str] = []
    # Condition-driven numeric nutrient limits (nullable). Set from health conditions.
    max_sodium_mg: Optional[float] = None
    min_fiber_g: Optional[float] = None
    max_sugar_g: Optional[float] = None
    retrieval_query: str = Field(description="natural-language description of the ideal meal for this slot")
    rationale: str = ""


class DayConstraintPlan(BaseModel):
    slots: List[TimedMealConstraint]


class SuggestedNutritionTarget(BaseModel):
    calories_kcal: int
    protein_g: float
    carbs_g: float
    fat_g: float
    rationale: str = ""


class SuggestedSlot(BaseModel):
    meal_time: str
    name: str
    calories_pct: float


class SuggestedMealStructure(BaseModel):
    timed_meals_per_day: int
    slots: List[SuggestedSlot]


# ── LLM singleton ──────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _llm():
    from langchain_groq import ChatGroq
    return ChatGroq(model=GROQ_MODEL, temperature=0.2, api_key=os.getenv("GROQ_API_KEY"))


def _structured(schema, temperature: Optional[float] = None):
    llm = _llm()
    if temperature is not None:
        llm = llm.bind(temperature=temperature)
    return llm.with_structured_output(schema)


# ── Constraint generation (core call) ──────────────────────────────────────

_CONSTRAINT_SYSTEM = """You are a clinical nutrition planning assistant.
Given a user's profile, their daily macro target, and an optional meal structure,
produce ONE constraint object per meal slot. For each slot decide:
- macros: split the daily macro target across slots (all slots must sum to the daily totals)
- composition: which components (main, optionally side), whether dessert is allowed, item/serving bounds
- required_labels / preferred_labels: choose ONLY from the ALLOWED LABELS list provided below. Put diet
  preferences (vegetarian/vegan/halal) in required_labels. Do NOT invent labels (no 'low_sodium',
  'high_fiber', etc. — those go in the numeric fields or the query).
- max_sodium_mg / min_fiber_g / max_sugar_g: set these numeric limits from health conditions
  (hypertension -> low max_sodium_mg e.g. 500; diabetes -> low max_sugar_g e.g. 10 and min_fiber_g e.g. 6).
  Leave null when not relevant.
- retrieval_query: a short natural-language description of the ideal meal for this slot, reflecting the
  user's preferences, conditions and macros (used for semantic search — express open-ended health
  intent like 'low-sodium heart-healthy' HERE, not as labels).
Honor any user-pinned structure (slot count, meal_time, name, labels, calories %). Keep it realistic."""


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
        plan: DayConstraintPlan = _structured(DayConstraintPlan).invoke(
            [("system", _CONSTRAINT_SYSTEM), ("human", user_msg)]
        )
        if plan and plan.slots:
            if allowed:
                for s in plan.slots:  # strip any hallucinated labels
                    s.required_labels = [l for l in s.required_labels if l in allowed]
                    s.preferred_labels = [l for l in s.preferred_labels if l in allowed]
            return plan
    except Exception as e:  # noqa: BLE001
        print(f"[MealPlan] constraint LLM failed, using fallback: {e}")
    return _fallback_constraints(macro_target, slots)


def _fallback_constraints(macro_target: dict, slots: Optional[List[dict]]) -> DayConstraintPlan:
    if slots:
        base = slots
    else:
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
            retrieval_query=f"{s.get('name', s.get('meal_time', 'meal'))} meal",
            rationale="deterministic fallback",
        ))
    return DayConstraintPlan(slots=out)


# ── Setup suggestions (tool-callable) ──────────────────────────────────────

_MACRO_SYSTEM = """You are a nutrition assistant. Given a user's estimated daily energy needs (TDEE),
their goal and health conditions, return a daily nutrition target (calories + protein/carb/fat grams).
Adjust calories for the goal (lose: deficit ~15-20%, gain: surplus ~10-15%, maintain: ~TDEE) and
choose a sensible macro split, respecting conditions (e.g. diabetes -> lower carbs, higher fiber/protein)."""


def suggest_nutrition_target(tdee: int, goal_type: Optional[str], conditions: list, notes: Optional[str]) -> SuggestedNutritionTarget:
    user_msg = json.dumps({
        "tdee_kcal": tdee, "goal_type": goal_type,
        "health_conditions": conditions, "notes": notes,
    })
    try:
        return _structured(SuggestedNutritionTarget).invoke(
            [("system", _MACRO_SYSTEM), ("human", user_msg)]
        )
    except Exception as e:  # noqa: BLE001
        print(f"[MealPlan] macro LLM failed, using fallback: {e}")
        # Deterministic fallback: goal-adjusted calories, 30/40/30 split
        cal = tdee
        if goal_type == "lose":
            cal = int(tdee * 0.82)
        elif goal_type == "gain":
            cal = int(tdee * 1.12)
        return SuggestedNutritionTarget(
            calories_kcal=cal,
            protein_g=round(cal * 0.30 / 4, 1),
            carbs_g=round(cal * 0.40 / 4, 1),
            fat_g=round(cal * 0.30 / 9, 1),
            rationale="deterministic fallback",
        )


_STRUCTURE_SYSTEM = """You are a nutrition assistant. Suggest a daily meal structure (how many timed
meals and their names/times) for the user, given their profile. Return meal_time values from
breakfast/lunch/dinner/snack and calories_pct that sum to 100."""


def suggest_meal_structure(profile: dict) -> SuggestedMealStructure:
    try:
        return _structured(SuggestedMealStructure).invoke(
            [("system", _STRUCTURE_SYSTEM), ("human", json.dumps(profile, default=str))]
        )
    except Exception as e:  # noqa: BLE001
        print(f"[MealPlan] structure LLM failed, using fallback: {e}")
        return SuggestedMealStructure(
            timed_meals_per_day=4,
            slots=[
                SuggestedSlot(meal_time="breakfast", name="Breakfast", calories_pct=25),
                SuggestedSlot(meal_time="lunch", name="Lunch", calories_pct=35),
                SuggestedSlot(meal_time="dinner", name="Dinner", calories_pct=30),
                SuggestedSlot(meal_time="snack", name="Snack", calories_pct=10),
            ],
        )


# LangChain tool wrappers (usable by an agent; the endpoints call the functions directly).

@tool
def suggest_nutrition_target_tool(tdee: int, goal_type: Optional[str] = None,
                                  conditions: Optional[list] = None, notes: Optional[str] = None) -> dict:
    """Suggest a daily nutrition target (calories + protein/carb/fat grams) from TDEE, goal and conditions."""
    return suggest_nutrition_target(tdee, goal_type, conditions or [], notes).model_dump()


@tool
def suggest_meal_structure_tool(profile: dict) -> dict:
    """Suggest a daily meal structure (timed meals + calorie split) for a user profile."""
    return suggest_meal_structure(profile).model_dump()


SETUP_TOOLS = [suggest_nutrition_target_tool, suggest_meal_structure_tool]
