from __future__ import annotations

from sqlmodel import Session

from app.modules.appointment.models import ChatMessage, SessionNote, SessionRoom
from app.modules.appointment.services.session import (
    post_message,
    list_messages,
    upsert_note,
    get_note,
    start_session_room,   # ✅ must exist
    end_session_room,     # ✅ must exist
)


def send_message(session: Session, room_id: int, sender_user_id: int, message: str) -> ChatMessage:
    return post_message(session, room_id, sender_user_id, message)


def history(session: Session, room_id: int, user_id: int, limit: int = 200) -> list[ChatMessage]:
    return list_messages(session, room_id, user_id, limit=limit)


def write_note(session: Session, appointment_id: int, consultant_user_id: int, note: str, is_visible_to_user: bool) -> SessionNote:
    return upsert_note(session, appointment_id, consultant_user_id, note, is_visible_to_user)


def read_note(session: Session, appointment_id: int, requester_user_id: int) -> SessionNote:
    return get_note(session, appointment_id, requester_user_id)


# ✅ NEW lifecycle wrappers
def start_session(session: Session, appointment_id: int, consultant_user_id: int) -> SessionRoom:
    return start_session_room(session, appointment_id, consultant_user_id)


def end_session(session: Session, appointment_id: int, consultant_user_id: int) -> SessionRoom:
    return end_session_room(session, appointment_id, consultant_user_id)


def fetch_client_health(session: Session, appointment_id: int, consultant_user_id: int):
    from app.modules.appointment.services.session import get_client_health
    return get_client_health(session, appointment_id, consultant_user_id)


