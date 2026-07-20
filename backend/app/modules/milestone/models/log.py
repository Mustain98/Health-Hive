"""Milestone weight-log table (`user_goal_logs`). Was `UserGoalLog`."""
from datetime import datetime
from typing import Optional
import uuid

from sqlmodel import SQLModel, Field

from app.utils.time import utc_now


class MilestoneLog(SQLModel, table=True):
    """Weight check-ins against a milestone. Was `UserGoalLog`; table unchanged."""
    __tablename__ = "user_goal_logs"

    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    goal_id: uuid.UUID = Field(foreign_key="user_goals.id", index=True)
    date: datetime = Field(default_factory=utc_now)
    weight: float = Field(nullable=False)
    due_terget: float = Field(default=0.0)
