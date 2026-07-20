"""Nutrition-target table.

`__tablename__` is unchanged from when this lived in `user/models.py`
(`nutrition_targets`) — this module move needs no data migration.
"""
from datetime import datetime
from typing import Optional
import uuid

from sqlmodel import SQLModel, Field

from app.utils.time import utc_now
from app.modules.nutrition_target.schemas import (
    CALORIES_KCAL_MIN, CALORIES_KCAL_MAX,
    PROTEIN_G_MIN, PROTEIN_G_MAX,
    CARBS_G_MIN, CARBS_G_MAX,
    FAT_G_MIN, FAT_G_MAX,
)


class NutritionTarget(SQLModel, table=True):
    __tablename__ = "nutrition_targets"

    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    created_for: uuid.UUID = Field(foreign_key="users.id", index=True)
    created_by: uuid.UUID = Field(foreign_key="users.id", index=True)
    appointment_id: Optional[uuid.UUID] = Field(foreign_key="appointments.id", default=None, index=True)
    plan_id: Optional[uuid.UUID] = Field(default=None, index=True)  # groups this into a Plan
    active: bool = Field(default=False, nullable=False)
    calories_kcal: int = Field(ge=CALORIES_KCAL_MIN, le=CALORIES_KCAL_MAX)
    protein_g: float = Field(ge=PROTEIN_G_MIN, le=PROTEIN_G_MAX)
    carbs_g: float = Field(ge=CARBS_G_MIN, le=CARBS_G_MAX)
    fat_g: float = Field(ge=FAT_G_MIN, le=FAT_G_MAX)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
