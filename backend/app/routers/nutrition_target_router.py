from fastapi import APIRouter, Depends
from sqlmodel import Session
import uuid
from app.core.database import get_session
from app.core.auth import get_current_user
from app.models.user import User
from app.models.nutrition_target import NutritionTarget, NutritionTargetUpdate, NutritionTargetRead
from app.controller.nutrition_target_controller import get_my_target, upsert_my_target, get_my_all_targets

router = APIRouter(prefix="/nutrition-target", tags=["Nutrition Target"])

def _to_read(session: Session, target: NutritionTarget) -> NutritionTargetRead:
    res = NutritionTargetRead.model_validate(target)
    if target.created_by and target.created_by != target.created_for:
        creator = session.get(User, target.created_by)
        if creator:
            res.created_by_name = creator.full_name or creator.username
            res.created_by_email = creator.email
    return res

@router.get("/me", response_model=NutritionTargetRead)
def fetch_current_target(
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    target = get_my_target(session, me.id)
    return _to_read(session, target)


@router.get("/all", response_model=list[NutritionTargetRead])
def fetch_all_targets(
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    targets = get_my_all_targets(session, me.id)
    return [_to_read(session, t) for t in targets]


@router.put("/me", response_model=NutritionTargetRead)
def create_or_update_target(
    payload: NutritionTargetUpdate,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    target = upsert_my_target(session, me.id, payload)
    return _to_read(session, target)

@router.put("/{target_id}/activate", response_model=NutritionTargetRead)
def activate_target_endpoint(
    target_id: uuid.UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    from app.controller.nutrition_target_controller import activate_my_target
    target = activate_my_target(session, me.id, target_id)
    return _to_read(session, target)
