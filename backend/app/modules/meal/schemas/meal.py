from datetime import datetime
from typing import List, Optional
import uuid

from pydantic import BaseModel, ConfigDict
from sqlmodel import SQLModel

from app.modules.meal.models.meal import (
    FoodItemLabelName,
    MeasureUnit,
)

# Moved to app.modules.meal_plan_setting.schemas; re-exported so
# `from app.modules.meal.schemas import MealPlanSettingRead` keeps working.
from app.modules.meal_plan_setting.schemas import MealPlanSettingRead  # noqa: F401


# ── Food item schemas ──────────────────────────────────────────────────────

class FoodItemCreate(BaseModel):
    name: str
    description: Optional[str] = None
    nutrition_unit: MeasureUnit = MeasureUnit.gram
    weight_per_unit_g: Optional[float] = None

    calories: float = 0
    protein_g: float = 0
    carbs_g: float = 0
    fat_g: float = 0

    labels: List[FoodItemLabelName] = []


class FoodItemRead(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    nutrition_unit: MeasureUnit
    weight_per_unit_g: Optional[float] = None

    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float

    is_verified: bool
    labels: List[str] = []

    model_config = ConfigDict(from_attributes=True)


# MealPlanSettingRead moved to app.modules.meal_plan_setting.schemas
# (re-exported at the top of this file).
