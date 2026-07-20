"""Nutrition-target schemas — the daily calorie + macro target of a Plan.

Bounds are kept in lockstep with the `NutritionTarget` columns. Before this module
existed, `NutritionTargetUpdate` had no bounds at all, so the PATCH route accepted
values the model itself rejects. See `_BOUNDS` below.
"""
from datetime import datetime
from typing import Optional
import uuid

from sqlmodel import SQLModel, Field


# Single source of truth for the target bounds, shared by the table columns
# (nutrition_target/models.py) and the DTOs below.
CALORIES_KCAL_MIN, CALORIES_KCAL_MAX = 800, 10000
PROTEIN_G_MIN, PROTEIN_G_MAX = 0, 400
CARBS_G_MIN, CARBS_G_MAX = 0, 1200
FAT_G_MIN, FAT_G_MAX = 0, 300


class NutritionTargetUpdate(SQLModel):
    calories_kcal: Optional[int] = Field(default=None, ge=CALORIES_KCAL_MIN, le=CALORIES_KCAL_MAX)
    protein_g: Optional[float] = Field(default=None, ge=PROTEIN_G_MIN, le=PROTEIN_G_MAX)
    carbs_g: Optional[float] = Field(default=None, ge=CARBS_G_MIN, le=CARBS_G_MAX)
    fat_g: Optional[float] = Field(default=None, ge=FAT_G_MIN, le=FAT_G_MAX)
    active: bool = False


class NutritionTargetRead(SQLModel):
    id: uuid.UUID
    created_for: uuid.UUID
    created_by: uuid.UUID
    appointment_id: Optional[uuid.UUID] = None
    plan_id: Optional[uuid.UUID] = None
    active: bool
    calories_kcal: int
    protein_g: float
    carbs_g: float
    fat_g: float
    created_at: datetime
    updated_at: datetime
