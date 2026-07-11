from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlmodel import Session, select

from app.modules.appointment.models import (
    Appointment,
    AppointmentStatus,
    SessionRoom,
    SessionStatus,
)


def utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def cancel_appointment(session: Session, *, user_id: uuid.UUID, appointment_id: uuid.UUID) -> Appointment:
    appt = session.get(Appointment, appointment_id)
    if not appt:
        raise HTTPException(404, "Appointment not found")
    if appt.user_id != user_id:
        raise HTTPException(403, "Not your appointment")
    if appt.status != AppointmentStatus.scheduled:
        raise HTTPException(400, "Only scheduled appointments can be cancelled")

    now = utc_now_naive()
    appt.status = AppointmentStatus.cancelled
    appt.updated_at = now
    session.add(appt)

    room = session.exec(select(SessionRoom).where(SessionRoom.appointment_id == appointment_id)).first()
    if room:
        room.status = SessionStatus.ended
        room.ended_at = now
        room.ended_by_user_id = user_id
        room.updated_at = now
        session.add(room)

    session.commit()
    session.refresh(appt)
    return appt
