from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models.user_data import UserData
from app.schemas.user_data import UserDataUpdate


def _utc_now():
    return datetime.now(timezone.utc)


def _get_user_data_for_user(session: Session, user_id: int) -> UserData | None:
    return session.exec(select(UserData).where(UserData.user_id == user_id)).first()


def get_current_user_data(session: Session, user_id: int) -> UserData:
    data = _get_user_data_for_user(session, user_id)
    if not data:
        raise HTTPException(status_code=404, detail="User data not found.")
    return data


def create_or_update_user_data(session: Session, user_id: int, payload: UserDataUpdate) -> UserData:
    data = _get_user_data_for_user(session, user_id)

    if not data:
        data = UserData(user_id=user_id)
        session.add(data)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(data, field, value)

    data.updated_at = _utc_now()
    session.add(data)
    session.commit()
    session.refresh(data)

    # ✅ No automatic goal / nutrition target generation anymore (manual only).
    return data
