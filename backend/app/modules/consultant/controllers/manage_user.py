from __future__ import annotations

import uuid
from sqlmodel import Session

from app.modules.milestone.models import Milestone
from app.modules.nutrition_target.models import NutritionTarget
from app.modules.nutrition_target.schemas import NutritionTargetUpdate
from datetime import date

from app.modules.consultant.services.manage_user import (
    consultant_read_goal,
    consultant_create_goal,
    consultant_read_target,
    consultant_create_target,
    consultant_read_meal_plan_setting,
    consultant_create_meal_plan_setting,
    consultant_read_daily_goals,
    consultant_read_daily_goal_logs,
    consultant_read_plans,
    consultant_build_plan,
)


def read_user_goal(session: Session, consultant_user_id: uuid.UUID, user_id: uuid.UUID) -> Milestone:
    return consultant_read_goal(session, consultant_user_id, user_id)


def create_user_goal(session: Session, consultant_user_id: uuid.UUID, user_id: uuid.UUID, payload: Milestone, appointment_id: uuid.UUID | None = None) -> Milestone:
    return consultant_create_goal(session, consultant_user_id, user_id, payload, appointment_id=appointment_id)


def read_user_target(session: Session, consultant_user_id: uuid.UUID, user_id: uuid.UUID) -> NutritionTarget:
    return consultant_read_target(session, consultant_user_id, user_id)


def create_user_target(session: Session, consultant_user_id: uuid.UUID, user_id: uuid.UUID, payload: NutritionTargetUpdate, appointment_id: uuid.UUID | None = None) -> NutritionTarget:
    return consultant_create_target(session, consultant_user_id, user_id, payload, appointment_id=appointment_id)

def read_user_meal_plan_setting(session: Session, consultant_user_id: uuid.UUID, user_id: uuid.UUID):
    return consultant_read_meal_plan_setting(session, consultant_user_id, user_id)

def create_user_meal_plan_setting(session: Session, consultant_user_id: uuid.UUID, user_id: uuid.UUID, payload: dict, appointment_id: uuid.UUID | None = None):
    return consultant_create_meal_plan_setting(session, consultant_user_id, user_id, payload, appointment_id=appointment_id)


def read_user_daily_goals(session: Session, consultant_user_id: uuid.UUID, user_id: uuid.UUID) -> list[dict]:
    return consultant_read_daily_goals(session, consultant_user_id, user_id)


def read_user_daily_goal_logs(session: Session, consultant_user_id: uuid.UUID, user_id: uuid.UUID,
                              start: date | None = None, end: date | None = None) -> list[dict]:
    return consultant_read_daily_goal_logs(session, consultant_user_id, user_id, start, end)


def read_user_plans(session: Session, consultant_user_id: uuid.UUID, user_id: uuid.UUID) -> list[dict]:
    return consultant_read_plans(session, consultant_user_id, user_id)


def build_user_plan(session: Session, consultant_user_id: uuid.UUID, user_id: uuid.UUID, payload: dict) -> dict:
    return consultant_build_plan(session, consultant_user_id, user_id, payload)
