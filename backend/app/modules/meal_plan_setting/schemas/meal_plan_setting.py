"""Meal-plan-setting DTOs."""
from datetime import datetime
from typing import List, Optional
import uuid

from app.modules.meal_plan_setting.models import (
    MealPlanSettingBase,
    MealPlanSettingTimedMeal,
)


class MealPlanSettingRead(MealPlanSettingBase):
    id: uuid.UUID
    created_for: uuid.UUID
    created_by: uuid.UUID
    appointment_id: Optional[uuid.UUID] = None
    active: bool
    created_at: datetime
    updated_at: datetime
    timed_meals: List[MealPlanSettingTimedMeal] = []
