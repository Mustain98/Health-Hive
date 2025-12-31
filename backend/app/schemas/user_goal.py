from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import model_validator
from sqlmodel import SQLModel


from app.models.user_goal import GoalType


class GoalUpsert(SQLModel):
    goal_type: GoalType
    target_delta_kg: Optional[float] = None
    duration_days: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    @model_validator(mode="after")
    def _validate_goal(self):
        if self.goal_type == GoalType.maintain:
            if self.target_delta_kg is not None:
                raise ValueError("target_delta_kg must be null for maintain goal")
        else:
            if self.target_delta_kg is None or self.target_delta_kg <= 0:
                raise ValueError("target_delta_kg must be > 0 for lose/gain goals")

        if self.duration_days is None and (self.start_date is None or self.end_date is None):
            raise ValueError("Provide either duration_days OR both start_date and end_date")

        if self.duration_days is not None and self.duration_days <= 0:
            raise ValueError("duration_days must be > 0")

        if self.start_date is not None and self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("end_date must be >= start_date")

        return self


class GoalRead(SQLModel):
    id: int
    user_id: int
    goal_type: GoalType
    target_delta_kg: Optional[float]
    duration_days: Optional[int]
    start_date: Optional[date]
    end_date: Optional[date]
    created_at: datetime
    updated_at: datetime
