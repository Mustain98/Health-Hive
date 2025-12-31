from datetime import datetime, date, timezone
from enum import Enum
from typing import Optional

from sqlmodel import SQLModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class GoalType(str, Enum):
    lose = "lose"
    gain = "gain"
    maintain = "maintain"


class UserGoalBase(SQLModel):
    goal_type: GoalType
    target_delta_kg: Optional[float] = Field(default=None, gt=0)  
    duration_days: Optional[int] = Field(default=None, gt=0)

    start_date: Optional[date] = None
    end_date: Optional[date] = None



class UserGoal(UserGoalBase, table=True):
    __tablename__ = "user_goals"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True,unique=True)

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)