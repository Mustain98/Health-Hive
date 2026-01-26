from __future__ import annotations

from sqlmodel import Session

from app.models.user_goal import UserGoal
from app.models.nutrition_target import NutritionTarget
from app.schemas.user_goal import GoalUpsert
from app.schemas.nutrition_target import NutritionTargetUpdate
from app.service.consultant_manage_user_service import (
    consultant_read_goal,
    consultant_upsert_goal,
    consultant_read_target,
    consultant_upsert_target,
)


def read_user_goal(session: Session, consultant_user_id: int, user_id: int) -> UserGoal:
    return consultant_read_goal(session, consultant_user_id, user_id)


def upsert_user_goal(session: Session, consultant_user_id: int, user_id: int, payload: GoalUpsert, appointment_id: int | None = None) -> UserGoal:
    return consultant_upsert_goal(session, consultant_user_id, user_id, payload, appointment_id=appointment_id)


def read_user_target(session: Session, consultant_user_id: int, user_id: int) -> NutritionTarget:
    return consultant_read_target(session, consultant_user_id, user_id)


def upsert_user_target(session: Session, consultant_user_id: int, user_id: int, payload: NutritionTargetUpdate, appointment_id: int | None = None) -> NutritionTarget:
    return consultant_upsert_target(session, consultant_user_id, user_id, payload, appointment_id=appointment_id)
