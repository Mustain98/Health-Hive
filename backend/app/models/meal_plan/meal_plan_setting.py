from datetime import datetime, timezone
from typing import List, Optional
import uuid

from sqlmodel import Field, Relationship, SQLModel

from .meal import MealTimeType


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MealPlanSettingBase(SQLModel):
    name: str = Field(max_length=255, index=True)
    timed_meals_per_day: int = Field(ge=1, le=12)


class MealPlanSetting(MealPlanSettingBase, table=True):
    __tablename__ = "meal_plan_setting"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    created_for: uuid.UUID = Field(foreign_key="users.id", index=True)
    created_by: uuid.UUID = Field(foreign_key="users.id", index=True)
    appointment_id: Optional[uuid.UUID] = Field(default=None, foreign_key="appointments.id", index=True)
    active: bool = Field(default=False, nullable=False)

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    timed_meals: List["MealPlanSettingTimedMeal"] = Relationship(
        back_populates="meal_plan_setting"
    )


class MealPlanSettingTimedMealBase(SQLModel):
    name: str = Field(max_length=100)
    meal_time: MealTimeType = Field(index=True)

    calories_pct: float = Field(default=0, ge=0, le=100)
    protein_g_pct: float = Field(default=0, ge=0, le=100)
    carbs_g_pct: float = Field(default=0, ge=0, le=100)
    fat_g_pct: float = Field(default=0, ge=0, le=100)


class MealPlanSettingTimedMeal(MealPlanSettingTimedMealBase, table=True):
    __tablename__ = "meal_plan_setting_timed_meal"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    meal_plan_setting_id: uuid.UUID = Field(
        foreign_key="meal_plan_setting.id",
        index=True,
    )

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    meal_plan_setting: Optional["MealPlanSetting"] = Relationship(
        back_populates="timed_meals"
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