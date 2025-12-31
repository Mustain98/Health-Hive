from sqlmodel import Session

from app.models.user_goal import UserGoal
from app.schemas.user_goal import GoalUpsert
from app.service.user_goal_service import (
    get_goal_for_user,
    upsert_goal_for_user,
    delete_goal_for_user,
)


def get_my_goal(session: Session, user_id: int) -> UserGoal:
    return get_goal_for_user(session, user_id)


def upsert_my_goal(session: Session, user_id: int, payload: GoalUpsert) -> UserGoal:
    return upsert_goal_for_user(session, user_id, payload)


def delete_my_goal(session: Session, user_id: int) -> None:
    return delete_goal_for_user(session, user_id)
