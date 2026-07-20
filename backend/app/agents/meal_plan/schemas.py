"""Response schemas for the meal-plan agent.

These describe what the model must return for *constraint generation*; they are not
domain DTOs. The domain shapes (nutrition target, meal setting) live in their own
modules and are imported where needed.
"""
from typing import List, Optional

from pydantic import BaseModel, Field


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
    retrieval_query: str = Field(description=(
        "A rich 1-2 sentence description of the ideal meal for this slot, used for semantic "
        "search. Name concrete dishes/cuisines, key proteins and ingredients, cooking method "
        "and texture, and the health framing (e.g. 'low-sodium, high-fiber, heart-healthy'). "
        "Be specific and descriptive so it retrieves relevant meals."
    ))
    rationale: str = ""


class DayConstraintPlan(BaseModel):
    slots: List[TimedMealConstraint]
