from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlmodel import Session, select

from app.modules.appointment.models import SessionRoom, ChatMessage, Appointment, SessionNote, SessionStatus, AppointmentStatus


def _utc_now():
    return datetime.now(timezone.utc)


def _get_room(session: Session, room_id: int) -> SessionRoom:
    room = session.get(SessionRoom, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return room


def _get_appointment(session: Session, appointment_id: int) -> Appointment:
    appt = session.get(Appointment, appointment_id)
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appt


def _get_appointment_for_room(session: Session, room_id: int) -> tuple[SessionRoom, Appointment]:
    room = _get_room(session, room_id)
    appt = _get_appointment(session, room.appointment_id)
    return room, appt


def _get_room_by_appointment(session: Session, appointment_id: int) -> SessionRoom:
    room = session.exec(
        select(SessionRoom).where(SessionRoom.appointment_id == appointment_id)
    ).first()
    if not room:
        raise HTTPException(status_code=404, detail="Session room not found")
    return room


def _require_participant(appt: Appointment, user_id: int):
    if user_id not in (appt.user_id, appt.consultant_user_id):
        raise HTTPException(status_code=403, detail="Not a participant of this session")


def _require_consultant_owner(appt: Appointment, consultant_user_id: int):
    if appt.consultant_user_id != consultant_user_id:
        raise HTTPException(status_code=403, detail="Only the assigned consultant can do this")


def _deny_user_before_start(room: SessionRoom, appt: Appointment, requester_user_id: int):
    # user cannot view session before consultant starts
    if requester_user_id == appt.user_id and room.status == SessionStatus.not_started:
        raise HTTPException(status_code=403, detail="Session has not started yet")


# ---------------- Session lifecycle (NEW) ----------------

def start_session_room(session: Session, appointment_id: int, consultant_user_id: int) -> SessionRoom:
    appt = _get_appointment(session, appointment_id)
    _require_consultant_owner(appt, consultant_user_id)

    room = _get_room_by_appointment(session, appointment_id)

    if room.status == SessionStatus.ended:
        raise HTTPException(status_code=409, detail="Session already ended")

    if room.status != SessionStatus.active:
        room.status = SessionStatus.active
        room.started_at = room.started_at or _utc_now()
        room.started_by_user_id = consultant_user_id
        room.updated_at = _utc_now()
        session.add(room)
        session.commit()
        session.refresh(room)

    return room


def end_session_room(session: Session, appointment_id: int, consultant_user_id: int) -> SessionRoom:
    appt = _get_appointment(session, appointment_id)
    _require_consultant_owner(appt, consultant_user_id)

    room = _get_room_by_appointment(session, appointment_id)

    # Allow ending from any non-ended state (active OR not_started)
    if room.status == SessionStatus.ended:
        raise HTTPException(status_code=409, detail="Session already ended")

    room.status = SessionStatus.ended
    room.ended_at = _utc_now()
    room.ended_by_user_id = consultant_user_id
    room.updated_at = _utc_now()
    session.add(room)

    # ✅ Sync appointment status
    appt.status = AppointmentStatus.completed
    appt.updated_at = _utc_now()
    session.add(appt)

    session.commit()
    session.refresh(room)
    session.refresh(appt)


    return room


# ---------------- Chat ----------------

def post_message(session: Session, room_id: int, sender_user_id: int, message: str) -> ChatMessage:
    if not message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    room, appt = _get_appointment_for_room(session, room_id)
    _require_participant(appt, sender_user_id)

    # ✅ only ACTIVE can send
    if room.status != SessionStatus.active:
        raise HTTPException(status_code=403, detail="Session is not active")

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
    room, appt = _get_appointment_for_room(session, room_id)
    _require_participant(appt, user_id)

    # ✅ user cannot view before start
    _deny_user_before_start(room, appt, user_id)

    return list(
        session.exec(
            select(ChatMessage)
            .where(ChatMessage.room_id == room_id)
            .order_by(ChatMessage.sent_at.asc())
            .limit(limit)
        ).all()
    )


# ---------------- Notes ----------------

def upsert_note(
    session: Session,
    appointment_id: int,
    consultant_user_id: int,
    note: str,
    is_visible_to_user: bool,
) -> SessionNote:
    appt = _get_appointment(session, appointment_id)
    _require_consultant_owner(appt, consultant_user_id)

    room = _get_room_by_appointment(session, appointment_id)

    # ✅ notes locked unless ACTIVE
    if room.status != SessionStatus.active:
        raise HTTPException(status_code=403, detail="Session is not active; note is locked")

    existing = session.exec(
        select(SessionNote).where(SessionNote.appointment_id == appointment_id)
    ).first()

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
    appt = _get_appointment(session, appointment_id)
    _require_participant(appt, requester_user_id)

    room = _get_room_by_appointment(session, appointment_id)

    is_consultant = (requester_user_id == appt.consultant_user_id)

    # ✅ user cannot view before start; consultant can always view
    if not is_consultant:
        _deny_user_before_start(room, appt, requester_user_id)

    note = session.exec(
        select(SessionNote).where(SessionNote.appointment_id == appointment_id)
    ).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    # ✅ user can only read if visible; consultant always can read
    if not is_consultant and not note.is_visible_to_user:
        raise HTTPException(status_code=403, detail="Note not visible to user")

    return note


# ---------------- Client Health Data (Permissions) ----------------

def get_client_health(session: Session, appointment_id: int, consultant_user_id: int):
    from app.modules.user.models import User
    from app.modules.user.models import UserData
    from app.modules.user.models import UserGoal
    from app.modules.user.models import NutritionTarget

    appt = _get_appointment(session, appointment_id)
    _require_consultant_owner(appt, consultant_user_id)

    if not appt.consultant_access:
        raise HTTPException(status_code=403, detail="Permission to view health data not granted.")

    client = session.get(User, appt.user_id)
    user_data = session.exec(select(UserData).where(UserData.user_id == appt.user_id)).first()
    
    # Get active goal and target
    goal = session.exec(select(UserGoal).where(UserGoal.created_for == appt.user_id).where(UserGoal.active == True)).first()
    target = session.exec(select(NutritionTarget).where(NutritionTarget.created_for == appt.user_id).where(NutritionTarget.active == True)).first()

    return {
        "client": client,
        "user_data": user_data,
        "goal": goal,
        "nutrition_target": target
    }
