from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.auth import get_current_user
from app.core.database import get_session
from model import User
from app.modules.user import controller
from schema import (
    MessageResponse,
    TokenResponse,
    UserDataRead,
    UserDataUpdate,
    UserLogin,
    UserRead,
    UserRegister,
    UserUpdate,
)


router = APIRouter(prefix="/users", tags=["Users"])


# ── Auth Routes ───────────────────────────────────────────────────────────────

@router.post("/register", response_model=UserRead)
def register(
    data: UserRegister,
    session: Session = Depends(get_session),
):
    return controller.register_controller(
        session=session,
        data=data,
    )


@router.post("/login", response_model=TokenResponse)
def login(
    data: UserLogin,
    session: Session = Depends(get_session),
):
    return controller.login_controller(
        session=session,
        data=data,
    )


# ── Current User Routes ───────────────────────────────────────────────────────

@router.get("/me", response_model=UserRead)
def get_me():
    return get_current_user()
    


@router.get("/me/data", response_model=UserDataRead | None)
def get_my_data(
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    return controller.get_my_data_controller(
        session=session,
        me=me,
    )


@router.put("/me", response_model=UserRead)
def update_me(
    data: UserUpdate,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    return controller.update_me_controller(
        session=session,
        me=me,
        data=data,
    )


@router.put("/me/data", response_model=UserDataRead)
def update_my_data(
    data: UserDataUpdate,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    return controller.update_user_data(
        session=session,
        me=me,
        data=data,
    )


@router.delete("/me", response_model=MessageResponse)
def deactivate_me(
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    return controller.deactivate_me_controller(
        session=session,
        me=me,
    )

