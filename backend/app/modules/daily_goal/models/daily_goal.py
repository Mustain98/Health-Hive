"""Daily-goal tables.

`__tablename__` values are unchanged from when these lived in `user/models.py`
(`daily_goals`, `daily_goal_logs`) — this module move needs no data migration.
"""
from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import JSON, Column
from sqlmodel import SQLModel, Field

from app.utils.time import utc_now
from app.core.units import sa_enum
from app.modules.daily_goal.schemas import DailyGoalType, DailyGoalUnit


class DailyGoal(SQLModel, table=True):
    """A daily habit that drives a milestone (e.g. 30 pushups/day, burn 300 kcal,
    daily protein intake). Core columns + dynamic `attributes`."""
    __tablename__ = "daily_goals"

    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    created_for: uuid.UUID = Field(foreign_key="users.id", index=True)
    created_by: uuid.UUID = Field(foreign_key="users.id", index=True)
    milestone_id: Optional[uuid.UUID] = Field(default=None, foreign_key="user_goals.id", index=True)
    plan_id: Optional[uuid.UUID] = Field(default=None, index=True)  # groups this into a Plan

    goal_type: DailyGoalType
    name: str = Field(max_length=255)
    target_value: Optional[float] = Field(default=None)
    # Closed vocabulary (was free text — this column held "sets of 10-15 reps").
    unit: Optional[DailyGoalUnit] = Field(
        default=None,
        sa_column=Column(sa_enum(DailyGoalUnit, name="ck_daily_goals_unit"), nullable=True),
    )
    active: bool = Field(default=False, nullable=False)
    # Weekdays this habit applies to (Mon=0 … Sun=6). None/[] = every day.
    days_of_week: Optional[list[int]] = Field(default=None, sa_column=Column(JSON, nullable=True))

    # Dynamic detail, e.g. {"exercise": "pushups", "reps": 30} or {"kcal": 300}.
    attributes: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False, server_default="{}"))

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
