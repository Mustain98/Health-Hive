from __future__ import annotations

from typing import Dict, Optional, Set
import uuid

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlmodel import Session

from app.core.database import get_session
from app.core.auth import get_current_user, require_user_type
from app.modules.user.models import User, UserType
from app.modules.consultation import service as svc
from app.modules.consultation.models import (
    RequestStatus,
    ConsultationRequestCreate,
    ConsultationReplyRequest,
    ConsultationRequestRead,
    ConsultationChatRead,
    ConsultationMessageCreate,
    ConsultationMessageRead,
    ConsultationProposalCreate,
    ConsultationProposalRead,
)

router = APIRouter(prefix="/consultations", tags=["Consultations"])


# ─── Requests ────────────────────────────────────────────────────────────────

@router.post("/requests", response_model=ConsultationRequestRead)
def create_request(
    payload: ConsultationRequestCreate,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    req = svc.create_request(session, me.id, payload.consultant_user_id, payload.issue)
    return svc._enrich_request(session, req, me.id)


@router.get("/requests/me", response_model=list[ConsultationRequestRead])
def my_requests(
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    return svc.list_my_requests(session, me.id)


@router.get("/requests/incoming", response_model=list[ConsultationRequestRead])
def incoming_requests(
    status: Optional[RequestStatus] = None,
    session: Session = Depends(get_session),
    me: User = Depends(require_user_type(UserType.consultant)),
):
    return svc.list_incoming_requests(session, me.id, status)


@router.post("/requests/{request_id}/reply", response_model=ConsultationChatRead)
def reply_request(
    request_id: uuid.UUID,
    payload: ConsultationReplyRequest,
    session: Session = Depends(get_session),
    me: User = Depends(require_user_type(UserType.consultant)),
):
    chat = svc.reply_to_request(session, request_id, me.id, payload.message)
    return svc._enrich_chat(session, chat, me.id)


@router.post("/requests/{request_id}/decline", response_model=ConsultationRequestRead)
def decline_request(
    request_id: uuid.UUID,
    session: Session = Depends(get_session),
    me: User = Depends(require_user_type(UserType.consultant)),
):
    req = svc.decline_request(session, request_id, me.id)
    return svc._enrich_request(session, req, me.id)


# ─── Chats ───────────────────────────────────────────────────────────────────

@router.get("/chats/me", response_model=list[ConsultationChatRead])
def my_chats(
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    return svc.list_my_chats(session, me.id)


@router.get("/chats/{chat_id}", response_model=ConsultationChatRead)
def chat_detail(
    chat_id: uuid.UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    return svc.get_chat_detail(session, chat_id, me.id)


@router.get("/chats/{chat_id}/messages", response_model=list[ConsultationMessageRead])
def chat_messages(
    chat_id: uuid.UUID,
    skip: int = 0,
    limit: int = 200,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    return svc.list_messages(session, chat_id, me.id, skip=skip, limit=limit)


@router.post("/chats/{chat_id}/messages", response_model=ConsultationMessageRead)
def send_message(
    chat_id: uuid.UUID,
    payload: ConsultationMessageCreate,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    return svc.post_message(session, chat_id, me.id, payload.message)


# ─── Proposals ───────────────────────────────────────────────────────────────

@router.get("/chats/{chat_id}/proposals", response_model=list[ConsultationProposalRead])
def list_proposals(
    chat_id: uuid.UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    return svc.list_proposals(session, chat_id, me.id)


@router.post("/chats/{chat_id}/proposals", response_model=ConsultationProposalRead)
def propose_time(
    chat_id: uuid.UUID,
    payload: ConsultationProposalCreate,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    return svc.create_proposal(session, chat_id, me.id, payload.start_at, payload.end_at)


@router.post("/proposals/{proposal_id}/accept", response_model=ConsultationProposalRead)
def accept_proposal(
    proposal_id: uuid.UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    return svc.accept_proposal(session, proposal_id, me.id)


@router.post("/proposals/{proposal_id}/reject", response_model=ConsultationProposalRead)
def reject_proposal(
    proposal_id: uuid.UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    return svc.reject_proposal(session, proposal_id, me.id)


@router.post("/proposals/{proposal_id}/cancel", response_model=ConsultationProposalRead)
def cancel_proposal(
    proposal_id: uuid.UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    return svc.cancel_proposal(session, proposal_id, me.id)


# ─── WebSocket (optional real-time relay) ────────────────────────────────────

class ConnectionManager:
    def __init__(self):
        self.chats: Dict[uuid.UUID, Set[WebSocket]] = {}

    async def connect(self, chat_id: uuid.UUID, websocket: WebSocket):
        await websocket.accept()
        self.chats.setdefault(chat_id, set()).add(websocket)

    def disconnect(self, chat_id: uuid.UUID, websocket: WebSocket):
        if chat_id in self.chats:
            self.chats[chat_id].discard(websocket)
            if not self.chats[chat_id]:
                self.chats.pop(chat_id, None)

    async def broadcast(self, chat_id: uuid.UUID, payload: dict):
        for ws in list(self.chats.get(chat_id, set())):
            await ws.send_json(payload)


manager = ConnectionManager()


@router.websocket("/ws/{chat_id}")
async def ws_chat(websocket: WebSocket, chat_id: uuid.UUID):
    # Relay only; persistence happens via HTTP POST (which enforces permissions).
    await manager.connect(chat_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            await manager.broadcast(chat_id, data)
    except WebSocketDisconnect:
        manager.disconnect(chat_id, websocket)
