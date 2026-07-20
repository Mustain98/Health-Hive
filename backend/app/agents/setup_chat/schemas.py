"""Response schemas for the setup chatbot's `finalize` call.

LLM output is untrusted, so these are strict and bounded: an out-of-range value or an
invalid enum member is a parse error at the structured-output boundary rather than a
row in Postgres. Units and types reuse the canonical domain enums — they are not
re-declared here.
"""
from typing import List, Optional

from pydantic import BaseModel, Field

from app.modules.milestone.schemas import MilestoneType, MilestoneUnit
from app.modules.daily_goal.schemas import DailyGoalType, DailyGoalUnit


class SetupMilestone(BaseModel):
    milestone_type: MilestoneType
    name: str
    target_weight: Optional[float] = Field(default=None, ge=20, le=400)
    target_value: Optional[float] = Field(default=None, description="generic target, e.g. kg of muscle")
    unit: Optional[MilestoneUnit] = None
    duration_days: Optional[int] = Field(default=None, ge=1, le=1825)
    attributes: dict = {}


class SetupDailyGoal(BaseModel):
    goal_type: DailyGoalType
    name: str
    target_value: Optional[float] = None
    unit: Optional[DailyGoalUnit] = None
    attributes: dict = {}


class SetupNutritionTarget(BaseModel):
    calories_kcal: int = Field(ge=800, le=10000)
    protein_g: float = Field(ge=0, le=400)
    carbs_g: float = Field(ge=0, le=1200)
    fat_g: float = Field(ge=0, le=300)
    rationale: str = ""


class SetupSlot(BaseModel):
    meal_time: str = Field(description="MUST be exactly one of: breakfast, lunch, dinner, snack. "
                           "Use 'snack' for any extra eating occasion (mid-morning, brunch, pre-workout, etc.)")
    name: str
    calories_pct: float = Field(ge=0, le=100)
    protein_g_pct: float = Field(ge=0, le=100)
    carbs_g_pct: float = Field(ge=0, le=100)
    fat_g_pct: float = Field(ge=0, le=100)
    description: Optional[str] = Field(default=None, description="free-text guidance (foods, cuisines, health intent)")


class SetupMealSetting(BaseModel):
    name: str
    timed_meals_per_day: int = Field(ge=1, le=12)
    slots: List[SetupSlot]


class SetupFinalize(BaseModel):
    milestone: SetupMilestone
    daily_goals: List[SetupDailyGoal] = []
    nutrition_target: SetupNutritionTarget
    meal_setting: SetupMealSetting
    summary: str = ""
