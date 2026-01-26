from __future__ import annotations

from typing import Dict, Set

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlmodel import Session

from app.core.database import get_session
from app.core.auth import get_current_user
from app.models.user import User
from app.schemas.appointments import (
    ChatMessageCreate,
    ChatMessageRead,
    SessionNoteCreate,
    SessionNoteRead,
    SessionRoomRead,   # ✅ make sure you have this schema
)
from app.controller.session_controller import (
    send_message,
    history,
    write_note,
    read_note,
    start_session,
    end_session,
)

router = APIRouter(prefix="/sessions", tags=["Sessions"])


# ---------------- Session lifecycle (NEW) ----------------

@router.post("/appointments/{appointment_id}/start", response_model=SessionRoomRead)
def start_session_endpoint(
    appointment_id: int,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    # consultant-only enforced in service
    return start_session(session, appointment_id, me.id)


@router.post("/appointments/{appointment_id}/end", response_model=SessionRoomRead)
def end_session_endpoint(
    appointment_id: int,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    # consultant-only enforced in service
    return end_session(session, appointment_id, me.id)


# ---------------- Chat ----------------

@router.get("/rooms/{room_id}/messages", response_model=list[ChatMessageRead])
def get_messages(
    room_id: int,
    limit: int = 200,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    # ✅ service enforces: user cannot read before start, both can read after end
    return history(session, room_id, me.id, limit=limit)


@router.post("/rooms/{room_id}/messages", response_model=ChatMessageRead)
def post_message(
    room_id: int,
    payload: ChatMessageCreate,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    # ✅ service enforces: only ACTIVE can post
    return send_message(session, room_id, me.id, payload.message)


# ---------------- Notes ----------------

@router.put("/appointments/{appointment_id}/note", response_model=SessionNoteRead)
def upsert_session_note(
    appointment_id: int,
    payload: SessionNoteCreate,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    # ✅ service enforces: consultant-only + ACTIVE only (locked after end)
    return write_note(session, appointment_id, me.id, payload.note, payload.is_visible_to_user)


@router.get("/appointments/{appointment_id}/note", response_model=SessionNoteRead)
def get_session_note(
    appointment_id: int,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    # ✅ service enforces: user cannot read before start, visibility rules, etc.
    return read_note(session, appointment_id, me.id)


# ---------------- Client Health ----------------

@router.get("/appointments/{appointment_id}/client-health")
def get_client_health_data(
    appointment_id: int,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    from app.controller.session_controller import fetch_client_health
    # Service enforces permissions
    return fetch_client_health(session, appointment_id, me.id)


# ---------------- Session Permissions ----------------

from app.schemas.consultant_access import ConsultantPermissionRead, ConsultantPermissionCreate
from app.controller.session_controller import grant_session_permission, get_session_permission

@router.get("/appointments/{appointment_id}/permissions", response_model=list[ConsultantPermissionRead])
def get_permissions(
    appointment_id: int,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    # Retrieve permissions related to this session/users
    return get_session_permission(session, appointment_id, me.id)


@router.put("/appointments/{appointment_id}/permissions", response_model=ConsultantPermissionRead)
def update_permissions(
    appointment_id: int,
    payload: ConsultantPermissionCreate,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    # Only user can grant/update permissions for their own session
    return grant_session_permission(session, appointment_id, me.id, payload.scope, payload.resources)


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
async def ws_room(websocket: WebSocket, room_id: int):
    # For MVP, relay only. Persistence happens via HTTP POST (which enforces status).
    await manager.connect(room_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            await manager.broadcast(room_id, data)
    except WebSocketDisconnect:
        manager.disconnect(room_id, websocket)
