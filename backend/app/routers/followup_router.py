from __future__ import annotations

from typing import Dict, List, Set
from uuid import UUID
import uuid

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlmodel import Session

from app.core.database import get_session
from app.core.auth import get_current_user
from app.models.user import User
from app.models.appointments import Appointment
from app.models.followup import (
    FollowUpRoom,
    FollowUpMessage,
    FollowUpMessageRead,
    FollowUpRoomRead,
    TimeProposal,
    TimeProposalRead,
    SendMessageRequest,
    CreateProposalRequest,
)

router = APIRouter(prefix="/followup", tags=["Follow-up"])


# ─── Create from session (consultant only) ─────────────────────────────────────

@router.post("/from-session/{appointment_id}", response_model=FollowUpRoomRead)
def create_from_session(
    appointment_id: UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """
    Consultant calls this from within an active session to start a follow-up.
    The originating appointment is immediately linked (followup_room_id stamped).
    Returns existing room if one already exists for this (user, consultant) pair.
    """
    from app.service.followup_service import create_followup_from_session, _enrich_room
    room = create_followup_from_session(session, appointment_id, me.id)
    return _enrich_room(session, room, me.id)


# ─── Room management ───────────────────────────────────────────────────────────

@router.get("/rooms", response_model=list[FollowUpRoomRead])
def list_my_rooms(
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    from app.service.followup_service import list_rooms_for_user
    return list_rooms_for_user(session, me.id)


@router.get("/rooms/{room_id}", response_model=FollowUpRoomRead)
def get_room(
    room_id: UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    from app.service.followup_service import get_room_detail
    return get_room_detail(session, room_id, me.id)


@router.post("/rooms/{room_id}/cancel", response_model=FollowUpRoomRead)
def cancel_room(
    room_id: UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """Either the user or the consultant can cancel (close) a follow-up."""
    from app.service.followup_service import cancel_followup, _enrich_room
    room = cancel_followup(session, room_id, me.id)
    return _enrich_room(session, room, me.id)


# ─── Sessions list ─────────────────────────────────────────────────────────────

@router.get("/rooms/{room_id}/sessions", response_model=list[Appointment])
def get_sessions(
    room_id: UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """
    Return all appointments linked to this follow-up, ordered chronologically.
    The originating session is always first.
    """
    from app.service.followup_service import list_sessions_for_room
    return list_sessions_for_room(session, room_id, me.id)


# ─── Patient summary (consultant only) ─────────────────────────────────────────

@router.get("/rooms/{room_id}/patient-summary")
def get_patient_summary(
    room_id: UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """Consultant-only: returns patient UserData, active UserGoal, active NutritionTarget."""
    from app.service.followup_service import get_patient_summary as svc
    return svc(session, room_id, me.id)


@router.get("/rooms/{room_id}/my-summary")
def get_my_summary(
    room_id: UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """User-only: returns their own UserData, active UserGoal, NutritionTarget, and Goal Logs."""
    from app.service.followup_service import get_my_summary as svc
    return svc(session, room_id, me.id)


# ─── Messages ──────────────────────────────────────────────────────────────────

@router.get("/rooms/{room_id}/messages", response_model=list[FollowUpMessageRead])
def get_messages(
    room_id: UUID,
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    from app.service.followup_service import list_messages
    return list_messages(session, room_id, me.id, skip=skip, limit=limit)


@router.post("/rooms/{room_id}/messages", response_model=FollowUpMessageRead)
def send_message(
    room_id: UUID,
    payload: SendMessageRequest,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    from app.service.followup_service import post_message
    return post_message(session, room_id, me.id, payload.message)


# ─── Proposals ─────────────────────────────────────────────────────────────────

@router.get("/rooms/{room_id}/proposals", response_model=list[TimeProposalRead])
def get_proposals(
    room_id: UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    from app.service.followup_service import list_proposals
    return list_proposals(session, room_id, me.id)


@router.post("/rooms/{room_id}/proposals", response_model=TimeProposalRead)
def create_proposal(
    room_id: UUID,
    payload: CreateProposalRequest,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    from app.service.followup_service import create_proposal as svc_create
    return svc_create(session, room_id, me.id, payload.start_at, payload.end_at)


@router.post("/proposals/{proposal_id}/accept", response_model=TimeProposalRead)
def accept_proposal(
    proposal_id: UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    from app.service.followup_service import accept_proposal as svc_accept
    return svc_accept(session, proposal_id, me.id)


@router.post("/proposals/{proposal_id}/reject", response_model=TimeProposalRead)
def reject_proposal(
    proposal_id: UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    from app.service.followup_service import reject_proposal as svc_reject
    return svc_reject(session, proposal_id, me.id)


@router.post("/proposals/{proposal_id}/cancel", response_model=TimeProposalRead)
def cancel_proposal(
    proposal_id: UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    from app.service.followup_service import cancel_proposal as svc_cancel
    return svc_cancel(session, proposal_id, me.id)


# ─── WebSocket real-time relay ──────────────────────────────────────────────────

class FollowUpConnectionManager:
    def __init__(self):
        self.rooms: Dict[UUID, Set[WebSocket]] = {}

    async def connect(self, room_id: UUID, ws: WebSocket):
        await ws.accept()
        self.rooms.setdefault(room_id, set()).add(ws)

    def disconnect(self, room_id: UUID, ws: WebSocket):
        self.rooms.get(room_id, set()).discard(ws)
        if not self.rooms.get(room_id):
            self.rooms.pop(room_id, None)

    async def broadcast(self, room_id: UUID, payload: dict):
        for ws in list(self.rooms.get(room_id, set())):
            try:
                await ws.send_json(payload)
            except Exception:
                pass


manager = FollowUpConnectionManager()


@router.websocket("/ws/{room_id}")
async def ws_followup(websocket: WebSocket, room_id: UUID):
    """Real-time message relay. Clients must also POST /messages for persistence."""
    await manager.connect(room_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            await manager.broadcast(room_id, data)
    except WebSocketDisconnect:
        manager.disconnect(room_id, websocket)
