from datetime import date, timedelta

from sqlmodel import Session, select

from app.models.user_goal import UserGoal
from app.schemas.user_goal import GoalUpsert, GoalType
from app.service.user_goal_service import upsert_goal_for_user
from app.utils.calculate import calculate_bmi  # your BMI function


def suggested_goal_from_bmi(weight_kg: float, height_cm: float,) -> GoalUpsert:
    bmi = calculate_bmi(weight_kg, height_cm)
    h_m = height_cm / 100.0
    #proxy day calculaion for now
    days=28

    # target weight at BMI boundary
    if bmi < 18.5:
        target_weight = 18.5 * (h_m ** 2)
        delta = max(target_weight - weight_kg, 0.0)
        goal_type = GoalType.gain
        target_delta = round(delta, 2) if delta > 0 else None
    elif bmi > 25:
        target_weight = 25.0 * (h_m ** 2)
        delta = max(weight_kg - target_weight, 0.0)
        goal_type = GoalType.lose
        target_delta = round(delta, 2) if delta > 0 else None
    else:
        goal_type = GoalType.maintain
        target_delta = None

    start = date.today()
    end = start + timedelta(days=days - 1)

    return GoalUpsert(
        goal_type=goal_type,
        target_delta_kg=target_delta,
        duration_days=days,
        start_date=start,
        end_date=end,
    )


def adjust_goal_if_none(session: Session, user_id: int, weight_kg: float, height_cm: float) -> None:
    """
    Only create an auto goal if the user does NOT already have an active goal.
    """
    existing_goal = session.exec(select(UserGoal).where(UserGoal.user_id == user_id)).first()
    if existing_goal:
        return

    payload = suggested_goal_from_bmi(weight_kg, height_cm)
    upsert_goal_for_user(session, user_id, payload)
