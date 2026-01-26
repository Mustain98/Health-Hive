from datetime import datetime, date
from typing import Optional

from sqlmodel import SQLModel, Field

from app.models.user_data import utc_now  


class NutritionTargetBase(SQLModel):
    calories_kcal: int = Field(ge=800, le=10000)
    protein_g: float = Field(ge=0, le=400)
    carbs_g: float = Field(ge=0, le=1200)
    fat_g: float = Field(ge=0, le=300)

class NutritionTarget(NutritionTargetBase, table=True):
    __tablename__ = "nutrition_targets"

    id:int = Field(default=None, primary_key=True,index=True)
    user_id: int = Field(foreign_key="users.id", index=True,unique=True)

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
