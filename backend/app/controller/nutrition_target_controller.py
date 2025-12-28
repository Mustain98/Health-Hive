from __future__ import annotations

from fastapi import HTTPException
from sqlmodel import Session

from app.models.nutrition_target import NutritionTarget
from app.schemas.nutrition_target import NutritionTargetUpdate
from app.service.nutrition_target_service import get_current_target, upsert_target_manual


def get_my_target(session: Session, user_id: int) -> NutritionTarget:
    t = get_current_target(session, user_id)
    if not t:
        raise HTTPException(status_code=404, detail="Nutrition target not found.")
    return t


def upsert_my_target(session: Session, user_id: int, payload: NutritionTargetUpdate) -> NutritionTarget:
    return upsert_target_manual(session, user_id, payload)
