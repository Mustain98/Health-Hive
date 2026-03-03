from sqlmodel import Session
import uuid

from app.models.user_goal import UserGoal
from app.service.user_goal_service import (
    get_goal_for_user,
    upsert_goal_for_user,
    delete_goal_for_user,
    activate_goal_for_user,
    get_goals_for_user,
)


def get_my_goal(session: Session, user_id: uuid.UUID) -> UserGoal:
    return get_goal_for_user(session, user_id)


def get_my_all_goals(session: Session, user_id: uuid.UUID) -> list[UserGoal]:
    return get_goals_for_user(session, user_id)


def upsert_my_goal(session: Session, user_id: uuid.UUID, payload: UserGoal) -> UserGoal:
    return upsert_goal_for_user(session, user_id, payload)


def delete_my_goal(session: Session, user_id: uuid.UUID) -> None:
    return delete_goal_for_user(session, user_id)


def activate_my_goal(session: Session, user_id: uuid.UUID, goal_id: uuid.UUID) -> UserGoal:
    return activate_goal_for_user(session, user_id, goal_id)
