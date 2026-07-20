"""Meal-plan-setting tables — how a Plan splits the day's meals.

`__tablename__` values are unchanged from when these lived in `meal/models.py`
(`meal_plan_setting`, `meal_plan_setting_timed_meal`) — no data migration needed.

`MealTimeType` / `MealLabelName` come from `app.core.enums`, NOT from `meal.models`.
That is deliberate: `meal/models.py` re-exports this module's tables for back-compat,
so importing the enums from there would make the two modules import each other.
"""
from datetime import datetime
from typing import List, Optional
import uuid

from sqlalchemy import JSON, Column
from sqlmodel import Field, Relationship, SQLModel

from app.utils.time import utc_now
from app.core.enums import MealTimeType, MealLabelName


class MealPlanSettingBase(SQLModel):
    name: str = Field(max_length=255, index=True)
    timed_meals_per_day: int = Field(ge=1, le=12)


class MealPlanSetting(MealPlanSettingBase, table=True):
    __tablename__ = "meal_plan_setting"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    created_for: uuid.UUID = Field(foreign_key="users.id", index=True)
    created_by: uuid.UUID = Field(foreign_key="users.id", index=True)
    appointment_id: Optional[uuid.UUID] = Field(default=None, foreign_key="appointments.id", index=True)
    plan_id: Optional[uuid.UUID] = Field(default=None, index=True)  # groups this into a Plan
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

    # Free-text guidance for this slot (may mention food items, cuisines, labels, etc.).
    # The LLM already considers everything, so hard-coded labels are no longer required.
    description: Optional[str] = Field(default=None)

    # Optional/legacy label hints (kept for back-compat; no longer required). Stored as JSON.
    meal_labels: List[MealLabelName] = Field(default=[], sa_column=Column(JSON, nullable=False, default=[]))


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
