from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models.appointments import SessionRoom, ChatMessage, Appointment, SessionNote, SessionStatus, AppointmentStatus


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

    if room.status != SessionStatus.active:
        raise HTTPException(status_code=409, detail="Session is not active")

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

    # ✅ Auto-revoke permission on end
    from app.service.permission_service import revoke_permission
    revoke_permission(session, appt.user_id, consultant_user_id)

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

    # ✅ user cannot view before start
    _deny_user_before_start(room, appt, requester_user_id)

    note = session.exec(
        select(SessionNote).where(SessionNote.appointment_id == appointment_id)
    ).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    # ✅ user can only read if visible
    if requester_user_id == appt.user_id and not note.is_visible_to_user:
        raise HTTPException(status_code=403, detail="Note not visible to user")

    return note


# ---------------- Client Health Data (Permissions) ----------------

from app.service.permission_service import assert_permission
from app.models.user_goal import UserGoal
from app.models.nutrition_target import NutritionTarget
from app.models.user import User

def get_client_health(session: Session, appointment_id: int, consultant_user_id: int):
    appt = _get_appointment(session, appointment_id)
    _require_consultant_owner(appt, consultant_user_id)

    room = _get_room_by_appointment(session, appointment_id)

    # ✅ Strict rule: view only if ACTIVE (optional choice, but recommended for security)
    if room.status != SessionStatus.active:
        raise HTTPException(status_code=403, detail="Session is not active; cannot view client health data")

    # ✅ Check for 'user_data' resource permission
    # Automatically checks: user_id, consultant_id, active permission, correct granted_in_appointment_id (if we enforce strict linkage there, but currently assert_permission checks active status. We might want to enforce appointment linkage too).
    # For now, assert_permission checks if *any* active permission exists for these users with this resource.
    # To enforce exact appointment scoping, assert_permission needs update or we check here manually?
    # The requirement said: "permission used for a session MUST be tied to that appointment via granted_in_appointment_id"
    
    perm = assert_permission(session, appt.user_id, consultant_user_id, "user_data", write=False)
    
    # Verify strict session scope
    if perm.granted_in_appointment_id != appointment_id:
         raise HTTPException(status_code=403, detail="Permission not granted for this specific session")

    # Fetch data
    from app.models.user_data import UserData
    client = session.get(User, appt.user_id)
    user_data = session.exec(select(UserData).where(UserData.user_id == appt.user_id)).first()
    goal = session.exec(select(UserGoal).where(UserGoal.user_id == appt.user_id)).first()
    target = session.exec(select(NutritionTarget).where(NutritionTarget.user_id == appt.user_id)).first()

    return {
        "client": client,
        "user_data": user_data,
        "goal": goal,
        "nutrition_target": target
    }


# ---------------- Session Permissions ----------------

from app.service.permission_service import grant_permission, list_permissions_for_user
from app.models.consultant_access import ConsultantPermission, PermissionScope

def manage_session_permission(
    session: Session, 
    appointment_id: int, 
    user_id: int, 
    scope: str, 
    resources: list[str]
) -> ConsultantPermission:
    appt = _get_appointment(session, appointment_id)
    
    # Only the CLIENT (user_id) can grant permission
    if appt.user_id != user_id:
        raise HTTPException(status_code=403, detail="Only the client can manage permissions for this session")

    room = _get_room_by_appointment(session, appointment_id)
    
    # Strict rule: can only update permissions if active? Or allow before?
    # User request: "Calls PUT ... Once granted, consultant health panel should work."
    # Recommend: Allow anytime, but usefulness is mostly during session.
    # Let's verify room status if desired. For now, allow always or strict? 
    # "permissions used for a session MUST be tied to that appointment via granted_in_appointment_id"
    # "Automatically set granted_in_appointment_id = appointment_id"
    
    return grant_permission(
        session,
        user_id=appt.user_id,
        consultant_user_id=appt.consultant_user_id,
        scope=PermissionScope(scope),
        resources=resources,
        granted_in_appointment_id=appointment_id
    )


def list_session_permissions(session: Session, appointment_id: int, requester_user_id: int) -> list[ConsultantPermission]:
    appt = _get_appointment(session, appointment_id)
    _require_participant(appt, requester_user_id)
    
    # Filter only for this appointment's pair
    # reusing list_permissions_for_user but we might want to filter specific logic
    perms = list_permissions_for_user(session, appt.user_id)
    return [p for p in perms if p.consultant_user_id == appt.consultant_user_id]
