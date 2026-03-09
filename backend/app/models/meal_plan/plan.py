from datetime import date, datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, List, Optional
import uuid

from sqlmodel import Field, Relationship, SQLModel


if TYPE_CHECKING:
    from .meal import TimedMeal


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PlanStatus(str, Enum):
    draft = "draft"
    active = "active"
    completed = "completed"


class WeekMealPlanBase(SQLModel):
    title: str = Field(max_length=255, index=True)
    start_date: date = Field(index=True)
    end_date: date = Field(index=True)
    status: PlanStatus = Field(default=PlanStatus.draft, index=True)


class WeekMealPlan(WeekMealPlanBase, table=True):
    __tablename__ = "week_meal_plan"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id", index=True)

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    day_plans: List["DayMealPlan"] = Relationship(back_populates="week_plan")


class DayMealPlanBase(SQLModel):
    plan_date: date = Field(index=True)
    note: Optional[str] = None


class DayMealPlan(DayMealPlanBase, table=True):
    __tablename__ = "day_meal_plan"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    week_plan_id: uuid.UUID = Field(foreign_key="week_meal_plan.id", index=True)

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    week_plan: Optional["WeekMealPlan"] = Relationship(back_populates="day_plans")
    timed_meals: List["TimedMeal"] = Relationship(back_populates="day_plan")