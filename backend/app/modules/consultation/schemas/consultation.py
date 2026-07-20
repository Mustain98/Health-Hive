from __future__ import annotations

from datetime import datetime
from typing import Optional
import uuid

from sqlmodel import SQLModel

from app.modules.consultation.models.consultation import RequestStatus, ChatStatus, ProposalStatus


# ── Requests ───────────────────────────────────────────────────────────────

class ConsultationRequestCreate(SQLModel):
    consultant_user_id: uuid.UUID
    issue: str


class ConsultationReplyRequest(SQLModel):
    message: str


class ConsultationRequestRead(SQLModel):
    id: uuid.UUID
    user_id: uuid.UUID
    consultant_user_id: uuid.UUID
    issue: str
    status: RequestStatus
    chat_id: Optional[uuid.UUID] = None
    responded_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    # Enriched by the service for list views
    other_party_name: Optional[str] = None
    other_party_email: Optional[str] = None


# ── Chats ──────────────────────────────────────────────────────────────────

class ConsultationChatRead(SQLModel):
    id: uuid.UUID
    request_id: uuid.UUID
    user_id: uuid.UUID
    consultant_user_id: uuid.UUID
    status: ChatStatus
    last_message_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    # Enriched by the service
    other_party_name: Optional[str] = None
    other_party_email: Optional[str] = None


# ── Messages ───────────────────────────────────────────────────────────────

class ConsultationMessageCreate(SQLModel):
    message: str


class ConsultationMessageRead(SQLModel):
    id: uuid.UUID
    chat_id: uuid.UUID
    sender_user_id: uuid.UUID
    message: str
    is_system: bool
    sent_at: datetime


# ── Proposals ──────────────────────────────────────────────────────────────

class ConsultationProposalCreate(SQLModel):
    start_at: datetime
    end_at: datetime


class ConsultationProposalRead(SQLModel):
    id: uuid.UUID
    chat_id: uuid.UUID
    proposed_by_user_id: uuid.UUID
    start_at: datetime
    end_at: datetime
    status: ProposalStatus
    responded_by_user_id: Optional[uuid.UUID] = None
    responded_at: Optional[datetime] = None
    appointment_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime
