"""Safety guard for milestones.

The AI never *handles* risky cases and no entry point (manual CRUD included) may
create/activate a dangerous target — the guard only **flags** (never clamps), and
the caller refers the user to a consultant.

Split out of the former `user/risk.py`; the daily-goal half lives in
`daily_goal/risk.py`. The two share no internals beyond `CONSULT_HINT`.
"""
from math import ceil
from typing import Optional
import uuid

from fastapi import HTTPException
from sqlmodel import Session, select

from app.modules.user.models import UserData
from app.modules.milestone.models import Milestone
from app.modules.milestone.schemas import MilestoneType
from app.utils.calculate import calculate_bmi

# Conservative thresholds — flag only.
MIN_HEALTHY_BMI = 18.5
MAX_WEEKLY_LOSS_FRACTION = 0.01     # >1% of bodyweight per week
MAX_WEEKLY_GAIN_KG = 0.5            # weight or muscle

# Upper end of the healthy BMI band. Informational only: `is_risky_milestone` does NOT
# flag targets above it (wanting to gain into the upper healthy range is legitimate),
# but proposals should stay inside the band.
MAX_HEALTHY_BMI = 24.9

CONSULT_HINT = "Please consult a consultant to set this up safely."


def _user_data(session: Session, user_id: uuid.UUID) -> Optional[UserData]:
    return session.exec(select(UserData).where(UserData.user_id == user_id)).first()


# ── Safe envelope (read-only; the AI plans inside it) ──────────────────────
# The guard above says "no". These say "here is what yes looks like" — derived from the
# same constants, so a threshold change moves both together. Pure functions: no DB, so
# the tool layer, the finalize path and error messages can all call them.

def safe_bounds(height_cm: float, weight_kg: float) -> dict:
    """The envelope a milestone proposal must stay inside for this body."""
    height_m = height_cm / 100.0
    return {
        "current_bmi": calculate_bmi(weight_kg, height_cm),
        "bmi_status": bmi_status(calculate_bmi(weight_kg, height_cm)),
        "min_healthy_weight_kg": round(MIN_HEALTHY_BMI * height_m ** 2, 1),
        "max_healthy_weight_kg": round(MAX_HEALTHY_BMI * height_m ** 2, 1),
        "max_weekly_loss_kg": round(MAX_WEEKLY_LOSS_FRACTION * weight_kg, 2),
        "max_weekly_gain_kg": MAX_WEEKLY_GAIN_KG,
    }


def bmi_status(bmi: float) -> str:
    if bmi < MIN_HEALTHY_BMI:
        return "underweight"
    if bmi > MAX_HEALTHY_BMI:
        return "overweight"
    return "healthy"


def max_weekly_change_kg(current_weight_kg: float, target_weight_kg: float) -> float:
    """The rate ceiling that applies in the direction of travel."""
    if target_weight_kg < current_weight_kg:
        return MAX_WEEKLY_LOSS_FRACTION * current_weight_kg
    return MAX_WEEKLY_GAIN_KG


def min_safe_duration_days(current_weight_kg: float, target_weight_kg: float) -> Optional[int]:
    """Shortest duration (whole weeks) in which this target is reachable safely."""
    if not current_weight_kg or not target_weight_kg:
        return None
    delta = abs(target_weight_kg - current_weight_kg)
    if delta == 0:
        return None
    return ceil(delta / max_weekly_change_kg(current_weight_kg, target_weight_kg)) * 7


def is_risky_milestone(session: Session, user_id: uuid.UUID, goal: Milestone) -> Optional[str]:
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

    # Muscle gain expressed via target_value (kg of muscle) — recomposition gains
    # muscle too, so the same realism ceiling applies.
    if goal.milestone_type in (MilestoneType.gain_muscle, MilestoneType.recomposition) \
            and goal.target_value and weeks:
        weekly = goal.target_value / weeks
        if weekly > MAX_WEEKLY_GAIN_KG:
            return f"muscle-gain rate {weekly:.2f} kg/wk is unrealistic (> {MAX_WEEKLY_GAIN_KG} kg/week)"

    return None


def assert_safe_milestone(session: Session, user_id: uuid.UUID, goal: Milestone) -> None:
    reason = is_risky_milestone(session, user_id, goal)
    if reason:
        raise HTTPException(status_code=422, detail=f"This goal looks unsafe: {reason}. {CONSULT_HINT}")
