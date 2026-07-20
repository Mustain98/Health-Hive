"""Safety guard for daily goals.

Flags only — never clamps. The caller refers the user to a consultant.
Split out of the former `user/risk.py`; the milestone half lives in
`milestone/risk.py`.
"""
from typing import Optional
import uuid

from fastapi import HTTPException
from sqlmodel import Session

from app.modules.daily_goal.models import DailyGoal
from app.modules.daily_goal.schemas import DailyGoalType, DailyGoalUnit

# Conservative thresholds — flag only.
MAX_DAILY_BURN_KCAL = 1500
MIN_DAILY_INTAKE_KCAL = 1200
MAX_DAILY_STEPS = 50000

CONSULT_HINT = "Please consult a consultant to set this up safely."


def is_risky_daily_goal(session: Session, user_id: uuid.UUID, dg: DailyGoal) -> Optional[str]:
    """Return a human reason if the daily goal is unsafe, else None."""
    tv = dg.target_value
    if dg.goal_type == DailyGoalType.calorie_burn and tv and tv > MAX_DAILY_BURN_KCAL:
        return f"daily calorie-burn target {tv:.0f} kcal is excessive (> {MAX_DAILY_BURN_KCAL})"
    if (
        dg.goal_type == DailyGoalType.intake
        and tv is not None
        # The old check also allowed the free-text unit "kcal/day"; the closed
        # vocabulary makes that unrepresentable, so only kcal (or unset) applies.
        and dg.unit in (None, DailyGoalUnit.kcal)
        and tv < MIN_DAILY_INTAKE_KCAL
    ):
        return f"daily intake target {tv:.0f} kcal is below a safe minimum ({MIN_DAILY_INTAKE_KCAL})"
    if dg.goal_type == DailyGoalType.steps and tv and tv > MAX_DAILY_STEPS:
        return f"daily steps target {tv:.0f} is unrealistic (> {MAX_DAILY_STEPS})"
    return None


def assert_safe_daily_goal(session: Session, user_id: uuid.UUID, dg: DailyGoal) -> None:
    reason = is_risky_daily_goal(session, user_id, dg)
    if reason:
        raise HTTPException(status_code=422, detail=f"This daily goal looks unsafe: {reason}. {CONSULT_HINT}")
