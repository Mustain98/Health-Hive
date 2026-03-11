from datetime import datetime, date, timezone
from enum import Enum
from typing import Optional
import uuid

from pydantic import model_validator
from sqlmodel import SQLModel, Field
from app.utils.time import utc_now


class GoalType(str, Enum):
    lose = "lose"
    gain = "gain"
    maintain = "maintain"




class UserGoal(SQLModel, table=True):
    __tablename__ = "user_goals"

    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    created_for: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id", index=True)
    created_by: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id", index=True)
    appointment_id: Optional[uuid.UUID] = Field(default=None, foreign_key="appointments.id", index=True)
    goal_type: GoalType
    target_weight: Optional[float] = Field(default=None, gt=0)      # Absolute target weight in kg
    initial_weight: Optional[float] = Field(default=None, gt=0)     # Weight at time of activation
    duration_days: Optional[int] = Field(default=None, gt=0)
    active:bool=Field(default=False,nullable=False)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class UserGoalUpdate(SQLModel):
    active:bool=Field(default_factory=False,nullable=False)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    updated_at: Optional[datetime]=utc_now

class GoalDateChangeRequest(SQLModel):
    new_start_date: date

class UserGoalRead(SQLModel):
    id: uuid.UUID
    created_for: Optional[uuid.UUID]
    created_by: Optional[uuid.UUID]
    appointment_id: Optional[uuid.UUID]
    goal_type: GoalType
    target_weight: Optional[float]
    initial_weight: Optional[float]
    duration_days: Optional[int]
    active: bool
    start_date: Optional[date]
    end_date: Optional[date]
    created_at: datetime
    updated_at: datetime
    created_by_name: Optional[str] = None
    created_by_email: Optional[str] = None