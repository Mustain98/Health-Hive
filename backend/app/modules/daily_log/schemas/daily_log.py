"""Daily-log schemas.

`DailyLogSubmit` is the daily-log *form*: one submission carries both the day's
calorie balance and the user's daily-goal completions. That is why this module
imports `DailyGoalCompletion` from `daily_goal/` — a one-way import from the
tracking module to the plan-part module. `daily_goal/` never imports this module.
"""
import datetime as _dt
from typing import List, Optional

from sqlmodel import SQLModel

from app.modules.daily_goal.schemas import DailyGoalCompletion


class DailyLogSubmit(SQLModel):
    # NB: use the module-qualified type — a field named `date` would otherwise
    # shadow the `date` type and resolve the annotation to NoneType.
    date: Optional[_dt.date] = None                   # client local date; defaults to today
    completions: List[DailyGoalCompletion] = []
    calories_in: Optional[float] = None
    calories_out: Optional[float] = None
