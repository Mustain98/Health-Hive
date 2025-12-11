from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.database import get_session
from app.core.auth import get_current_user
from app.models.user import User
from app.models.user_data import UserData
from app.schemas.user_data import (
    UserDataCreate,
    UserDataUpdate,
    UserDataRead,
)

user_data_router = APIRouter()


def _get_user_data_for_user(session: Session, user_id: int) -> UserData | None:
    return session.exec(
        select(UserData).where(UserData.user_id == user_id)
    ).first()


# ---------- Get current user's data ----------

@user_data_router.get("/user-data/me", response_model=UserDataRead)
def get_my_user_data(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    data = _get_user_data_for_user(session, current_user.id)
    if not data:
        raise HTTPException(status_code=404, detail="User data not found")
    return data


# ---------- Create (first time) current user's data ----------

@user_data_router.post("/user-data/me", response_model=UserDataRead)
def create_my_user_data(
    payload: UserDataCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    existing = _get_user_data_for_user(session, current_user.id)
    if existing:
        raise HTTPException(
            status_code=400,
            detail="User data already exists, use PUT to update",
        )

    data = UserData(
        user_id=current_user.id,
        **payload.model_dump(exclude_unset=True),
    )

    session.add(data)
    session.commit()
    session.refresh(data)
    return data


# ---------- Update (create-or-update) current user's data ----------

@user_data_router.put("/user-data/me", response_model=UserDataRead)
def upsert_my_user_data(
    payload: UserDataUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    data = _get_user_data_for_user(session, current_user.id)

    if not data:
        # If no record yet, create one
        data = UserData(
            user_id=current_user.id,
            **payload.model_dump(exclude_unset=True),
        )
        session.add(data)
    else:
        # Update only provided fields
        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(data, field, value)
        data.updated_at = datetime.now(timezone.utc)
        session.add(data)

    session.commit()
    session.refresh(data)
    return data
