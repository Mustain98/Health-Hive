from __future__ import annotations

import uuid
from sqlmodel import Session

from app.models.user_goal import UserGoal
from app.models.nutrition_target import NutritionTarget, NutritionTargetUpdate
from app.service.consultant_manage_user_service import (
    consultant_read_goal,
    consultant_create_goal,
    consultant_read_target,
    consultant_create_target,
    consultant_read_meal_plan_setting,
    consultant_create_meal_plan_setting,
)


def read_user_goal(session: Session, consultant_user_id: uuid.UUID, user_id: uuid.UUID) -> UserGoal:
    return consultant_read_goal(session, consultant_user_id, user_id)


def create_user_goal(session: Session, consultant_user_id: uuid.UUID, user_id: uuid.UUID, payload: UserGoal, appointment_id: uuid.UUID | None = None) -> UserGoal:
    return consultant_create_goal(session, consultant_user_id, user_id, payload, appointment_id=appointment_id)


def read_user_target(session: Session, consultant_user_id: uuid.UUID, user_id: uuid.UUID) -> NutritionTarget:
    return consultant_read_target(session, consultant_user_id, user_id)


def create_user_target(session: Session, consultant_user_id: uuid.UUID, user_id: uuid.UUID, payload: NutritionTargetUpdate, appointment_id: uuid.UUID | None = None) -> NutritionTarget:
    return consultant_create_target(session, consultant_user_id, user_id, payload, appointment_id=appointment_id)

def read_user_meal_plan_setting(session: Session, consultant_user_id: uuid.UUID, user_id: uuid.UUID):
    return consultant_read_meal_plan_setting(session, consultant_user_id, user_id)

def create_user_meal_plan_setting(session: Session, consultant_user_id: uuid.UUID, user_id: uuid.UUID, payload: dict, appointment_id: uuid.UUID | None = None):
    return consultant_create_meal_plan_setting(session, consultant_user_id, user_id, payload, appointment_id=appointment_id)
