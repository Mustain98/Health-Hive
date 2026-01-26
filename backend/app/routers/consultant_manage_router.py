from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.database import get_session
from app.core.auth import require_user_type
from app.models.user import User, UserType
from app.schemas.user_goal import GoalUpsert, GoalRead
from app.schemas.nutrition_target import NutritionTargetRead, NutritionTargetUpdate
from app.controller.consultant_manage_user_controller import (
    read_user_goal,
    upsert_user_goal,
    read_user_target,
    upsert_user_target,
)

router = APIRouter(prefix="/consultant", tags=["Consultant Actions"])


@router.get("/users/{user_id}/goal", response_model=GoalRead)
def consultant_get_user_goal(
    user_id: int,
    session: Session = Depends(get_session),
    me: User = Depends(require_user_type(UserType.consultant)),
):
    return read_user_goal(session, me.id, user_id)


@router.put("/users/{user_id}/goal", response_model=GoalRead)
def consultant_put_user_goal(
    user_id: int,
    payload: GoalUpsert,
    appointment_id: int | None = None,
    session: Session = Depends(get_session),
    me: User = Depends(require_user_type(UserType.consultant)),
):
    return upsert_user_goal(session, me.id, user_id, payload, appointment_id=appointment_id)


@router.get("/users/{user_id}/nutrition-target", response_model=NutritionTargetRead)
def consultant_get_user_target(
    user_id: int,
    session: Session = Depends(get_session),
    me: User = Depends(require_user_type(UserType.consultant)),
):
    return read_user_target(session, me.id, user_id)


@router.put("/users/{user_id}/nutrition-target", response_model=NutritionTargetRead)
def consultant_put_user_target(
    user_id: int,
    payload: NutritionTargetUpdate,
    appointment_id: int | None = None,
    session: Session = Depends(get_session),
    me: User = Depends(require_user_type(UserType.consultant)),
):
    return upsert_user_target(session, me.id, user_id, payload, appointment_id=appointment_id)
