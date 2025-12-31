from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.database import get_session
from app.core.auth import get_current_user
from app.models.user import User
from app.schemas.user_data import UserDataUpdate, UserDataRead
from app.controller.user_data_controller import (
    get_current_user_data,
    create_or_update_user_data,
)

user_data_router = APIRouter(prefix="/user-data", tags=["User Data"])


@user_data_router.get("/me", response_model=UserDataRead)
def get_my_user_data(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return get_current_user_data(session, current_user.id)


@user_data_router.put("/me", response_model=UserDataRead)
def upsert_my_user_data(
    payload: UserDataUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return create_or_update_user_data(session, current_user.id, payload)
