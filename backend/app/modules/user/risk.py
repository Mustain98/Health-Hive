"""Safety guard for goals/daily goals.

The AI never *handles* risky cases and no entry point (manual CRUD included) may
create/activate a dangerous target — the guard only **flags** (never clamps), and
the caller refers the user to a consultant. See docs/implementation.md decision 3.
"""
from typing import Optional
import uuid

from fastapi import HTTPException
from sqlmodel import Session, select

from app.modules.user.models import UserData, UserGoal, DailyGoal
from app.modules.user.schemas import MilestoneType, DailyGoalType
from app.utils.calculate import calculate_bmi

# Conservative thresholds — flag only.
MIN_HEALTHY_BMI = 18.5
MAX_WEEKLY_LOSS_FRACTION = 0.01     # >1% of bodyweight per week
MAX_WEEKLY_GAIN_KG = 0.5            # weight or muscle
MAX_DAILY_BURN_KCAL = 1500
MIN_DAILY_INTAKE_KCAL = 1200
MAX_DAILY_STEPS = 50000

CONSULT_HINT = "Please consult a consultant to set this up safely."


def _user_data(session: Session, user_id: uuid.UUID) -> Optional[UserData]:
    return session.exec(select(UserData).where(UserData.user_id == user_id)).first()


def is_risky_milestone(session: Session, user_id: uuid.UUID, goal: UserGoal) -> Optional[str]:
    """Return a human reason if the milestone is unsafe, else None."""
    ud = _user_data(session, user_id)
    current_weight = goal.initial_weight or (ud.weight_kg if ud else None)
    weeks = (goal.duration_days / 7.0) if goal.duration_days else None

    # Target below a healthy BMI floor.
    if goal.target_weight and ud and ud.height_cm:
        target_bmi = calculate_bmi(goal.target_weight, ud.height_cm)
        if target_bmi < MIN_HEALTHY_BMI:
            return f"target weight implies BMI {target_bmi} (below healthy {MIN_HEALTHY_BMI})"

    # Weight change rate.
    if current_weight and goal.target_weight and weeks:
        delta = goal.target_weight - current_weight
        weekly = abs(delta) / weeks
        if delta < 0 and weekly > MAX_WEEKLY_LOSS_FRACTION * current_weight:
            return f"weight-loss rate {weekly:.2f} kg/wk exceeds ~1% of bodyweight per week"
        if delta > 0 and weekly > MAX_WEEKLY_GAIN_KG:
            return f"weight-gain rate {weekly:.2f} kg/wk exceeds {MAX_WEEKLY_GAIN_KG} kg/week"

    # Muscle gain expressed via target_value (kg of muscle).
    if goal.milestone_type == MilestoneType.gain_muscle and goal.target_value and weeks:
        weekly = goal.target_value / weeks
        if weekly > MAX_WEEKLY_GAIN_KG:
            return f"muscle-gain rate {weekly:.2f} kg/wk is unrealistic (> {MAX_WEEKLY_GAIN_KG} kg/week)"

    return None


def is_risky_daily_goal(session: Session, user_id: uuid.UUID, dg: DailyGoal) -> Optional[str]:
    """Return a human reason if the daily goal is unsafe, else None."""
    tv = dg.target_value
    if dg.goal_type == DailyGoalType.calorie_burn and tv and tv > MAX_DAILY_BURN_KCAL:
        return f"daily calorie-burn target {tv:.0f} kcal is excessive (> {MAX_DAILY_BURN_KCAL})"
    if (
        dg.goal_type == DailyGoalType.intake
        and tv is not None
        and (dg.unit in (None, "kcal", "kcal/day"))
        and tv < MIN_DAILY_INTAKE_KCAL
    ):
        return f"daily intake target {tv:.0f} kcal is below a safe minimum ({MIN_DAILY_INTAKE_KCAL})"
    if dg.goal_type == DailyGoalType.steps and tv and tv > MAX_DAILY_STEPS:
        return f"daily steps target {tv:.0f} is unrealistic (> {MAX_DAILY_STEPS})"
    return None


def assert_safe_milestone(session: Session, user_id: uuid.UUID, goal: UserGoal) -> None:
    reason = is_risky_milestone(session, user_id, goal)
    if reason:
        raise HTTPException(status_code=422, detail=f"This goal looks unsafe: {reason}. {CONSULT_HINT}")


def assert_safe_daily_goal(session: Session, user_id: uuid.UUID, dg: DailyGoal) -> None:
    reason = is_risky_daily_goal(session, user_id, dg)
    if reason:
        raise HTTPException(status_code=422, detail=f"This daily goal looks unsafe: {reason}. {CONSULT_HINT}")
