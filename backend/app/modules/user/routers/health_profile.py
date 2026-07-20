from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.database import get_session
from app.core.auth import get_current_user
from app.modules.user.models import User, UserHealthProfile
from app.modules.user.schemas import UserHealthProfileRead, UserHealthProfileUpsert
from app.modules.user.services import health_profile as svc

router = APIRouter(prefix="/health-profile", tags=["Health Profile"])


@router.get("", response_model=UserHealthProfileRead)
def get_my_health_profile(
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    profile = svc.get_health_profile(session, me.id)
    if not profile:
        # Return an empty default profile (not yet set)
        from app.utils.time import utc_now
        now = utc_now()
        return UserHealthProfileRead(
            user_id=me.id, diet_preferences=[], health_conditions=[], notes=None,
            created_at=now, updated_at=now,
        )
    return profile


@router.put("", response_model=UserHealthProfileRead)
def upsert_my_health_profile(
    payload: UserHealthProfileUpsert,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    return svc.upsert_health_profile(
        session, me.id,
        payload.diet_preferences, payload.health_conditions, payload.notes,
    )
