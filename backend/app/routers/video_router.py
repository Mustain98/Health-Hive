from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.database import get_session
from app.core.auth import get_current_user
from app.models.user import User
from app.service.video_chat_service import (
    validate_join_for_appointment,
    create_agora_token,
)

router = APIRouter(prefix="/video", tags=["Video"])


@router.post("/appointments/{appointment_id}/join")
def join_video_session(
    appointment_id: UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    validate_join_for_appointment(session, me=me, appointment_id=appointment_id)

    payload = create_agora_token(
        appointment_id=appointment_id,
        user_id=me.id,
    )
    return payload