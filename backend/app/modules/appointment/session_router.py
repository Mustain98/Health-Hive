from __future__ import annotations

from typing import Dict, Set
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlmodel import Session

from app.core.database import get_session
from app.core.auth import get_current_user
from app.modules.user.models import User
from app.modules.appointment.models import (
    ChatMessageCreate,
    ChatMessage,
    SessionNoteCreate,
    SessionNote,
    SessionRoom,   # ✅ make sure you have this schema
)
from app.modules.appointment.session_controller import (
    send_message,
    history,
    write_note,
    read_note,
    start_session,
    end_session,
)

router = APIRouter(prefix="/sessions", tags=["Sessions"])


# ---------------- Session lifecycle (NEW) ----------------

@router.post("/appointments/{appointment_id}/start", response_model=SessionRoom)
def start_session_endpoint(
    appointment_id: UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    # consultant-only enforced in service
    return start_session(session, appointment_id, me.id)


@router.post("/appointments/{appointment_id}/end", response_model=SessionRoom)
def end_session_endpoint(
    appointment_id: UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    # consultant-only enforced in service
    return end_session(session, appointment_id, me.id)


# ---------------- Chat ----------------

@router.get("/rooms/{room_id}/messages", response_model=list[ChatMessage])
def get_messages(
    room_id: UUID,
    limit: int = 200,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    # ✅ service enforces: user cannot read before start, both can read after end
    return history(session, room_id, me.id, limit=limit)


@router.post("/rooms/{room_id}/messages", response_model=ChatMessage)
def post_message(
    room_id: UUID,
    payload: ChatMessageCreate,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    # ✅ service enforces: only ACTIVE can post
    return send_message(session, room_id, me.id, payload.message)


# ---------------- Notes ----------------

@router.put("/appointments/{appointment_id}/note", response_model=SessionNote)
def upsert_session_note(
    appointment_id: UUID,
    payload: SessionNoteCreate,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    # ✅ service enforces: consultant-only + ACTIVE only (locked after end)
    return write_note(session, appointment_id, me.id, payload.note, payload.is_visible_to_user)


@router.get("/appointments/{appointment_id}/note", response_model=SessionNote)
def get_session_note(
    appointment_id: UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    # ✅ service enforces: user cannot read before start, visibility rules, etc.
    return read_note(session, appointment_id, me.id)


@router.get("/appointments/{appointment_id}/notes", response_model=list[SessionNote])
def get_session_notes_list(
    appointment_id: UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """Get all notes for an appointment (convenience endpoint that returns a list)"""
    try:
        note = read_note(session, appointment_id, me.id)
        return [note] if note else []
    except Exception:
        return []


@router.get("/appointments/{appointment_id}/messages", response_model=list[ChatMessage])
def get_appointment_messages(
    appointment_id: UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """Get chat messages for an appointment (convenience endpoint)"""
    from app.modules.appointment.appointment_controller import get_room_id_for_appointment
    try:
        room_id = get_room_id_for_appointment(session, appointment_id)
        return history(session, room_id, me.id, limit=200)
    except Exception:
        return []


# ---------------- Client Health ----------------

@router.get("/appointments/{appointment_id}/client-health")
def get_client_health_data(
    appointment_id: UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    from app.modules.appointment.session_controller import fetch_client_health
    # Service enforces permissions
    return fetch_client_health(session, appointment_id, me.id)


# ---------------- WebSocket (optional real-time) ----------------

class ConnectionManager:
    def __init__(self):
        self.rooms: Dict[UUID, Set[WebSocket]] = {}

    async def connect(self, room_id: UUID, websocket: WebSocket):
        await websocket.accept()
        self.rooms.setdefault(room_id, set()).add(websocket)

    def disconnect(self, room_id: UUID, websocket: WebSocket):
        if room_id in self.rooms:
            self.rooms[room_id].discard(websocket)
            if not self.rooms[room_id]:
                self.rooms.pop(room_id, None)

    async def broadcast(self, room_id: UUID, payload: dict):
        for ws in list(self.rooms.get(room_id, set())):
            await ws.send_json(payload)

manager = ConnectionManager()


@router.websocket("/ws/rooms/{room_id}")
async def ws_room(websocket: WebSocket, room_id: UUID):
    # For MVP, relay only. Persistence happens via HTTP POST (which enforces status).
    await manager.connect(room_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            await manager.broadcast(room_id, data)
    except WebSocketDisconnect:
        manager.disconnect(room_id, websocket)
