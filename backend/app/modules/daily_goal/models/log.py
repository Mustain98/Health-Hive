"""Daily-goal completion log (`daily_goal_logs`)."""
from datetime import datetime
from typing import Optional
import uuid

from sqlmodel import SQLModel, Field

from app.utils.time import utc_now


class DailyGoalLog(SQLModel, table=True):
    """One row per daily goal per day — did the user complete it?"""
    __tablename__ = "daily_goal_logs"

    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    daily_goal_id: uuid.UUID = Field(foreign_key="daily_goals.id", index=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    date: datetime = Field(index=True)
    value: Optional[float] = Field(default=None)                   # actual achieved (e.g. 25 pushups)
    completed: bool = Field(default=False, nullable=False)
    created_at: datetime = Field(default_factory=utc_now)
