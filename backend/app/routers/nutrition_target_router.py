from fastapi import APIRouter, Depends
from sqlmodel import Session
import uuid
from app.core.database import get_session
from app.core.auth import get_current_user
from app.models.user import User
from app.models.nutrition_target import NutritionTarget, NutritionTargetUpdate
from app.controller.nutrition_target_controller import get_my_target, upsert_my_target, get_my_all_targets

router = APIRouter(prefix="/nutrition-target", tags=["Nutrition Target"])


@router.get("/me", response_model=NutritionTarget)
def fetch_current_target(
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    return get_my_target(session, me.id)


@router.get("/all", response_model=list[NutritionTarget])
def fetch_all_targets(
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    return get_my_all_targets(session, me.id)


@router.put("/me", response_model=NutritionTarget)
def create_or_update_target(
    payload: NutritionTargetUpdate,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    return upsert_my_target(session, me.id, payload)
@router.put("/{target_id}/activate", response_model=NutritionTarget)
def activate_target_endpoint(
    target_id: uuid.UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    from app.controller.nutrition_target_controller import activate_my_target
    return activate_my_target(session, me.id, target_id)
