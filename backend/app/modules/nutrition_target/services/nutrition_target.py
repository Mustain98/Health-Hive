from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
import uuid

from fastapi import HTTPException
from sqlmodel import Session, select

from app.modules.nutrition_target.models import NutritionTarget
from app.modules.nutrition_target.schemas import NutritionTargetUpdate


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def get_current_target(session: Session, user_id: uuid.UUID) -> Optional[NutritionTarget]:
    return session.exec(select(NutritionTarget).where(NutritionTarget.created_for == user_id).where(NutritionTarget.active == True)).first()


def get_targets_for_user(session: Session, user_id: uuid.UUID) -> list[NutritionTarget]:
    targets = session.exec(
        select(NutritionTarget)
        .where(NutritionTarget.created_for == user_id)
        .order_by(NutritionTarget.created_at.desc())
    ).all()
    return list(targets)


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


def create_target_for_user(
    session: Session, 
    user_id: uuid.UUID, 
    payload: NutritionTargetUpdate, 
    created_by: uuid.UUID,
    appointment_id: Optional[uuid.UUID] = None
) -> NutritionTarget:
    if (
        payload.calories_kcal is None
        or payload.protein_g is None
        or payload.carbs_g is None
        or payload.fat_g is None
    ):
         raise HTTPException(
            status_code=400,
            detail="Provide all fields (calories_kcal, protein_g, carbs_g, fat_g) to create.",
        )

    t = NutritionTarget(
        created_for=user_id,
        created_by=created_by,
        appointment_id=appointment_id,
        active=payload.active,
        calories_kcal=payload.calories_kcal,
        protein_g=payload.protein_g,
        carbs_g=payload.carbs_g,
        fat_g=payload.fat_g,
        created_at=_utc_now(),
        updated_at=_utc_now(),
    )

    if t.active:
         # Deactivate others
        existing_active = session.exec(select(NutritionTarget).where(NutritionTarget.created_for == user_id).where(NutritionTarget.active == True)).all()
        for ex in existing_active:
            ex.active = False
            session.add(ex)
        session.flush()  # deactivate before inserting the new active row (partial unique index)

    session.add(t)
    session.commit()
    session.refresh(t)
    return t


def activate_target_for_user(session: Session, user_id: uuid.UUID, target_id: uuid.UUID) -> NutritionTarget:
    # 1. Verify ownership
    target = session.get(NutritionTarget, target_id)
    if not target:
         raise HTTPException(status_code=404, detail="Target not found")
    if target.created_for != user_id:
         raise HTTPException(status_code=403, detail="Not your target")
    
    # 2. Deactivate currently active
    existing = session.exec(select(NutritionTarget).where(NutritionTarget.created_for == user_id).where(NutritionTarget.active == True)).all()
    for ex in existing:
        ex.active = False
        session.add(ex)
    session.flush()  # deactivate before activating target (partial unique index)

    # 3. Activate target
    target.active = True
    session.add(target)
    session.commit()
    session.refresh(target)
    return target
