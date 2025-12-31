from __future__ import annotations

from typing import Dict, Set

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlmodel import Session

from app.core.database import get_session
from app.core.auth import get_current_user
from app.models.user import User
from app.schemas.appointments import ChatMessageCreate, ChatMessageRead, SessionNoteCreate, SessionNoteRead
from app.controller.session_controller import send_message, history, write_note, read_note

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.get("/rooms/{room_id}/messages", response_model=list[ChatMessageRead])
def get_messages(
    room_id: int,
    limit: int = 200,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    return history(session, room_id, me.id, limit=limit)


@router.post("/rooms/{room_id}/messages", response_model=ChatMessageRead)
def post_message(
    room_id: int,
    payload: ChatMessageCreate,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    return send_message(session, room_id, me.id, payload.message)


@router.put("/appointments/{appointment_id}/note", response_model=SessionNoteRead)
def upsert_session_note(
    appointment_id: int,
    payload: SessionNoteCreate,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    # only consultant can write note (checked in service)
    return write_note(session, appointment_id, me.id, payload.note, payload.is_visible_to_user)


@router.get("/appointments/{appointment_id}/note", response_model=SessionNoteRead)
def get_session_note(
    appointment_id: int,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    return read_note(session, appointment_id, me.id)


# ---------------- WebSocket (optional real-time) ----------------

class ConnectionManager:
    def __init__(self):
        self.rooms: Dict[int, Set[WebSocket]] = {}

    async def connect(self, room_id: int, websocket: WebSocket):
        await websocket.accept()
        self.rooms.setdefault(room_id, set()).add(websocket)

    def disconnect(self, room_id: int, websocket: WebSocket):
        if room_id in self.rooms:
            self.rooms[room_id].discard(websocket)
            if not self.rooms[room_id]:
                self.rooms.pop(room_id, None)

    async def broadcast(self, room_id: int, payload: dict):
        for ws in list(self.rooms.get(room_id, set())):
            await ws.send_json(payload)

manager = ConnectionManager()


@router.websocket("/ws/rooms/{room_id}")
async def ws_room(
    websocket: WebSocket,
    room_id: int,
):
    # Auth in WS: expect Authorization: Bearer <token>
    # For MVP, we only accept and relay, persistence happens via HTTP POST.
    await manager.connect(room_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            await manager.broadcast(room_id, data)
    except WebSocketDisconnect:
        manager.disconnect(room_id, websocket)
