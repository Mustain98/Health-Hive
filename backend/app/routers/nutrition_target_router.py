from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.database import get_session
from app.core.auth import get_current_user
from app.models.user import User
from app.schemas.nutrition_target import NutritionTargetRead, NutritionTargetUpdate
from app.controller.nutrition_target_controller import get_my_target, upsert_my_target

router = APIRouter(prefix="/nutrition-target", tags=["Nutrition Target"])


@router.get("/me", response_model=NutritionTargetRead)
def fetch_current_target(
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    return get_my_target(session, me.id)


@router.put("/me", response_model=NutritionTargetRead)
def create_or_update_target(
    payload: NutritionTargetUpdate,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    return upsert_my_target(session, me.id, payload)
