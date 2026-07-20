"""Daily-log table — day-level calorie balance.

`__tablename__` is unchanged from when this lived in `user/models.py` (`daily_logs`)
— this module move needs no data migration.

This is *activity tracking*, not a plan part: it records what actually happened on a
given day, whereas `milestone/`, `daily_goal/`, `nutrition_target/` and
`meal_plan_setting/` describe what was planned.
"""
from datetime import datetime
from typing import Optional
import uuid

from sqlmodel import SQLModel, Field

from app.utils.time import utc_now


class DailyLog(SQLModel, table=True):
    """Day-level calorie balance captured by the daily log form."""
    __tablename__ = "daily_logs"

    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    date: datetime = Field(index=True)
    calories_in: Optional[float] = Field(default=None)
    calories_out: Optional[float] = Field(default=None)
    deficit_surplus: Optional[float] = Field(default=None)         # calories_in - calories_out
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
