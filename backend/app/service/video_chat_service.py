from __future__ import annotations

import os
import time
from fastapi import HTTPException
from sqlmodel import Session

from app.models.user import User
from app.models.appointments import SessionStatus
from app.service.session_service import _get_appointment, _get_room_by_appointment

try:
    from agora_token_builder import RtcTokenBuilder
except Exception as e:
    raise RuntimeError("Missing dependency: pip install agora-token-builder") from e

AGORA_APP_ID = os.getenv("AGORA_APP_ID")
AGORA_APP_CERT = os.getenv("AGORA_APP_CERTIFICATE")
AGORA_TTL = int(os.getenv("AGORA_TOKEN_TTL_SECONDS") or "2400")  # 40 min default


def _agora_channel_name(appointment_id: int) -> str:
    return f"appointment-{appointment_id}"


def _require_agora_env():
    if not AGORA_APP_ID:
        raise HTTPException(status_code=500, detail="AGORA_APP_ID is missing in env")
    if not AGORA_APP_CERT:
        raise HTTPException(status_code=500, detail="AGORA_APP_CERTIFICATE is missing in env")


def validate_join_for_appointment(session: Session, *, me: User, appointment_id: int):
    appt = _get_appointment(session, appointment_id)
    room = _get_room_by_appointment(session, appointment_id)

    if me.id not in (appt.user_id, appt.consultant_user_id):
        raise HTTPException(status_code=403, detail="You are not allowed in this session")

    if room.status == SessionStatus.ended:
        raise HTTPException(status_code=403, detail="Session has ended")

    if room.status != SessionStatus.active:
        raise HTTPException(status_code=403, detail="Session not started")

    return appt, room


def create_agora_token(*, appointment_id: int, uid: int) -> dict:
    """
    Returns { appId, channel, token, uid } for the frontend.
    """
    _require_agora_env()

    channel = _agora_channel_name(appointment_id)

    # Agora uid must be a 32-bit unsigned int. Your user ids are fine.
    if uid <= 0 or uid >= 2**32:
        raise HTTPException(status_code=400, detail="Invalid Agora uid")

    expire_ts = int(time.time()) + AGORA_TTL

    # Role:
    # For a normal 1:1 call where both users publish mic/cam, use "publisher" for both.
    ROLE_PUBLISHER = 1

    token = RtcTokenBuilder.buildTokenWithUid(
        AGORA_APP_ID,
        AGORA_APP_CERT,
        channel,
        uid,
        ROLE_PUBLISHER,
        expire_ts,
    )

    return {"appId": AGORA_APP_ID, "channel": channel, "token": token, "uid": uid}
