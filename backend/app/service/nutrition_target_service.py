from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models.nutrition_target import NutritionTarget
from app.schemas.nutrition_target import NutritionTargetUpdate


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def get_current_target(session: Session, user_id: int) -> Optional[NutritionTarget]:
    return session.exec(select(NutritionTarget).where(NutritionTarget.user_id == user_id)).first()


def upsert_target_manual(session: Session, user_id: int, payload: NutritionTargetUpdate) -> NutritionTarget:
    existing = get_current_target(session, user_id)

    if not existing:
        # require all fields on first create
        if (
            payload.calories_kcal is None
            or payload.protein_g is None
            or payload.carbs_g is None
            or payload.fat_g is None
        ):
            raise HTTPException(
                status_code=400,
                detail="Nutrition target not found. Provide all fields (calories_kcal, protein_g, carbs_g, fat_g) to create.",
            )

        t = NutritionTarget(
            user_id=user_id,
            calories_kcal=payload.calories_kcal,
            protein_g=payload.protein_g,
            carbs_g=payload.carbs_g,
            fat_g=payload.fat_g,
            created_at=_utc_now(),
            updated_at=_utc_now(),
        )
        session.add(t)
        session.commit()
        session.refresh(t)
        return t

    # partial update
    update_data = payload.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        if v is not None:
            setattr(existing, k, v)

    existing.updated_at = _utc_now()
    session.add(existing)
    session.commit()
    session.refresh(existing)
    return existing
