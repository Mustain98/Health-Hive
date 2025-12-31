from datetime import date, datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class NutritionTargetRead(SQLModel):
    id: int
    user_id: int

    calories_kcal: int
    protein_g: float
    carbs_g: float
    fat_g: float

    created_at: datetime
    updated_at: datetime


class NutritionTargetUpdate(SQLModel):
    calories_kcal: Optional[int] = Field(default=None, ge=800, le=10000)
    protein_g: Optional[float] = Field(default=None, ge=0, le=400)
    carbs_g: Optional[float] = Field(default=None, ge=0, le=1200)
    fat_g: Optional[float] = Field(default=None, ge=0, le=300)
