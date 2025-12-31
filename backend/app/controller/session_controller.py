from __future__ import annotations

from sqlmodel import Session

from app.models.appointments import ChatMessage, SessionNote
from app.service.session_service import post_message, list_messages, upsert_note, get_note


def send_message(session: Session, room_id: int, sender_user_id: int, message: str) -> ChatMessage:
    return post_message(session, room_id, sender_user_id, message)


def history(session: Session, room_id: int, user_id: int, limit: int = 200) -> list[ChatMessage]:
    return list_messages(session, room_id, user_id, limit=limit)


def write_note(session: Session, appointment_id: int, consultant_user_id: int, note: str, is_visible_to_user: bool) -> SessionNote:
    return upsert_note(session, appointment_id, consultant_user_id, note, is_visible_to_user)


def read_note(session: Session, appointment_id: int, requester_user_id: int) -> SessionNote:
    return get_note(session, appointment_id, requester_user_id)
