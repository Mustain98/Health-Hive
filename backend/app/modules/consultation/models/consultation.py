from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
import uuid

from sqlmodel import SQLModel, Field

from app.utils.time import utc_now


# ── Enums ──────────────────────────────────────────────────────────────────

class RequestStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    declined = "declined"


class ChatStatus(str, Enum):
    open = "open"
    closed = "closed"


class ProposalStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"
    cancelled = "cancelled"


# ── Tables ─────────────────────────────────────────────────────────────────

class ConsultationRequest(SQLModel, table=True):
    """A user 'knock' to a consultant stating an issue. Pending until the
    consultant replies (→ opens a chat) or declines. No chat exists yet."""
    __tablename__ = "consultation_requests"

    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    consultant_user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    issue: str
    status: RequestStatus = Field(default=RequestStatus.pending, index=True)
    # Plain column (not a FK) to avoid a circular FK with consultation_chats.
    # Set to the created chat's id when the consultant replies.
    chat_id: Optional[uuid.UUID] = Field(default=None, index=True)
    responded_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ConsultationChat(SQLModel, table=True):
    """The pre-booking chat box, created only when a consultant replies to a
    request. Distinct from a SessionRoom (which is the fixed consultation)."""
    __tablename__ = "consultation_chats"

    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    request_id: uuid.UUID = Field(foreign_key="consultation_requests.id", index=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    consultant_user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    status: ChatStatus = Field(default=ChatStatus.open, index=True)
    last_message_at: Optional[datetime] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ConsultationMessage(SQLModel, table=True):
    __tablename__ = "consultation_messages"

    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    chat_id: uuid.UUID = Field(foreign_key="consultation_chats.id", index=True)
    sender_user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    message: str
    is_system: bool = Field(default=False, index=True)
    sent_at: datetime = Field(default_factory=utc_now, index=True)


class ConsultationProposal(SQLModel, table=True):
    """A proposed time inside a chat. Accepting it books the fixed consultation
    (creates an Appointment + SessionRoom)."""
    __tablename__ = "consultation_proposals"

    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    chat_id: uuid.UUID = Field(foreign_key="consultation_chats.id", index=True)
    proposed_by_user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    start_at: datetime = Field(index=True)
    end_at: datetime = Field(index=True)
    status: ProposalStatus = Field(default=ProposalStatus.pending, index=True)
    responded_by_user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id")
    responded_at: Optional[datetime] = None
    appointment_id: Optional[uuid.UUID] = Field(default=None, foreign_key="appointments.id", index=True)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
