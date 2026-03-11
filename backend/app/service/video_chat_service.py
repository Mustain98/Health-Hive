from __future__ import annotations

import os
import time
import zlib
from typing import Any

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
AGORA_TTL = int(os.getenv("AGORA_TOKEN_TTL_SECONDS") or "2400")


def _require_agora_env() -> None:
    if not AGORA_APP_ID:
        raise HTTPException(status_code=500, detail="AGORA_APP_ID is missing in env")
    if not AGORA_APP_CERT:
        raise HTTPException(status_code=500, detail="AGORA_APP_CERTIFICATE is missing in env")


def _agora_channel_name(appointment_id: Any) -> str:
    # Works for UUID or int appointment ids
    return f"appointment-{appointment_id}"


def _to_agora_uid(value: Any) -> int:
    """
    Convert app user id (UUID/int/string) into a stable unsigned 32-bit int for Agora.
    """
    raw = str(value).strip()
    if not raw:
        raise HTTPException(status_code=400, detail="Invalid user id for Agora")

    uid = zlib.crc32(raw.encode("utf-8")) & 0xFFFFFFFF

    # Agora uid should be > 0
    if uid == 0:
        uid = 1

    return uid


def validate_join_for_appointment(session: Session, *, me: User, appointment_id: Any):
    appt = _get_appointment(session, appointment_id)
    room = _get_room_by_appointment(session, appointment_id)

    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    if not room:
        raise HTTPException(status_code=404, detail="Session room not found")

    if me.id not in (appt.user_id, appt.consultant_user_id):
        raise HTTPException(status_code=403, detail="You are not allowed in this session")

    if room.status == SessionStatus.ended:
        raise HTTPException(status_code=403, detail="Session has ended")

    if room.status != SessionStatus.active:
        raise HTTPException(status_code=403, detail="Session not started")

    return appt, room


def create_agora_token(*, appointment_id: Any, user_id: Any) -> dict:
    """
    Returns:
    {
      "appId": str,
      "channel": str,
      "token": str,
      "uid": int
    }
    """
    _require_agora_env()

    channel = _agora_channel_name(appointment_id)
    uid = _to_agora_uid(user_id)

    expire_ts = int(time.time()) + AGORA_TTL
    role_publisher = 1

    try:
        token = RtcTokenBuilder.buildTokenWithUid(
            AGORA_APP_ID,
            AGORA_APP_CERT,
            channel,
            uid,
            role_publisher,
            expire_ts,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create Agora token: {str(e)}")

    return {
        "appId": AGORA_APP_ID,
        "channel": channel,
        "token": token,
        "uid": uid,
    }