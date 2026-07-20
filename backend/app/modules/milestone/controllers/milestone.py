from sqlmodel import Session
import uuid

from app.modules.milestone.models import Milestone
from app.modules.milestone.services import (
    get_goal_for_user,
    create_goal_for_user,
    delete_goal_for_user,
    activate_goal_for_user,
    get_goals_for_user,
    change_goal_date
)


def get_my_goal(session: Session, user_id: uuid.UUID) -> Milestone:
    return get_goal_for_user(session, user_id)


def get_my_all_goals(session: Session, user_id: uuid.UUID) -> list[Milestone]:
    return get_goals_for_user(session, user_id)


def create_my_goal(session: Session, user_id: uuid.UUID, payload: Milestone) -> Milestone:
    return create_goal_for_user(session, user_id, payload)


def delete_my_goal(session: Session, user_id: uuid.UUID) -> None:
    return delete_goal_for_user(session, user_id)


def activate_my_goal(session: Session, user_id: uuid.UUID, goal_id: uuid.UUID) -> Milestone:
    return activate_goal_for_user(session, user_id, goal_id)

