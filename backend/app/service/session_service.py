from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models.appointments import SessionRoom, ChatMessage, Appointment, SessionNote


def _utc_now():
    return datetime.now(timezone.utc)


def _get_appointment_for_room(session: Session, room_id: int) -> Appointment:
    room = session.get(SessionRoom, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    appt = session.get(Appointment, room.appointment_id)
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appt


def assert_participant(session: Session, room_id: int, user_id: int) -> Appointment:
    appt = _get_appointment_for_room(session, room_id)
    if user_id not in (appt.user_id, appt.consultant_user_id):
        raise HTTPException(status_code=403, detail="Not a participant of this session")
    return appt


def post_message(session: Session, room_id: int, sender_user_id: int, message: str) -> ChatMessage:
    if not message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    assert_participant(session, room_id, sender_user_id)

    m = ChatMessage(
        room_id=room_id,
        sender_user_id=sender_user_id,
        message=message,
        sent_at=_utc_now(),
    )
    session.add(m)
    session.commit()
    session.refresh(m)
    return m


def list_messages(session: Session, room_id: int, user_id: int, limit: int = 200) -> list[ChatMessage]:
    assert_participant(session, room_id, user_id)
    return list(
        session.exec(
            select(ChatMessage)
            .where(ChatMessage.room_id == room_id)
            .order_by(ChatMessage.sent_at.asc())
            .limit(limit)
        ).all()
    )


def upsert_note(
    session: Session,
    appointment_id: int,
    consultant_user_id: int,
    note: str,
    is_visible_to_user: bool,
) -> SessionNote:
    appt = session.get(Appointment, appointment_id)
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if appt.consultant_user_id != consultant_user_id:
        raise HTTPException(status_code=403, detail="Only consultant can write session note")

    existing = session.exec(select(SessionNote).where(SessionNote.appointment_id == appointment_id)).first()
    now = _utc_now()
    if not existing:
        n = SessionNote(
            appointment_id=appointment_id,
            created_by_user_id=consultant_user_id,
            note=note,
            is_visible_to_user=is_visible_to_user,
            created_at=now,
            updated_at=now,
        )
        session.add(n)
        session.commit()
        session.refresh(n)
        return n

    existing.note = note
    existing.is_visible_to_user = is_visible_to_user
    existing.updated_at = now
    session.add(existing)
    session.commit()
    session.refresh(existing)
    return existing


def get_note(session: Session, appointment_id: int, requester_user_id: int) -> SessionNote:
    appt = session.get(Appointment, appointment_id)
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if requester_user_id not in (appt.user_id, appt.consultant_user_id):
        raise HTTPException(status_code=403, detail="Not a participant")

    note = session.exec(select(SessionNote).where(SessionNote.appointment_id == appointment_id)).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    # user can only read if visible, consultant always can
    if requester_user_id == appt.user_id and not note.is_visible_to_user:
        raise HTTPException(status_code=403, detail="Note not visible to user")
    return note
