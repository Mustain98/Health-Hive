from __future__ import annotations

from fastapi import HTTPException
from sqlmodel import Session
import uuid

from app.modules.user.models import NutritionTarget
from app.modules.user.models import NutritionTargetUpdate
from app.modules.user.nutrition_target_service import (
    get_current_target,
    upsert_target_manual,
    activate_target_for_user,
    get_targets_for_user,
)


def get_my_target(session: Session, user_id: uuid.UUID) -> NutritionTarget:
    t = get_current_target(session, user_id)
    if not t:
        raise HTTPException(status_code=404, detail="Nutrition target not found.")
    return t


def get_my_all_targets(session: Session, user_id: uuid.UUID) -> list[NutritionTarget]:
    return get_targets_for_user(session, user_id)


def upsert_my_target(session: Session, user_id: uuid.UUID, payload: NutritionTargetUpdate) -> NutritionTarget:
    return upsert_target_manual(session, user_id, payload)


def activate_my_target(session: Session, user_id: uuid.UUID, target_id: uuid.UUID) -> NutritionTarget:
    return activate_target_for_user(session, user_id, target_id)
