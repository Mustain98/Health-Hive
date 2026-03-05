from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
import uuid

from sqlmodel import SQLModel, Field

from app.utils.time import utc_now


class FollowUpRoomStatus(str, Enum):
    active = "active"
    closed = "closed"


class ProposalStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"
    cancelled = "cancelled"


class FollowUpRoom(SQLModel, table=True):
    __tablename__ = "followup_rooms"

    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    consultant_user_id: uuid.UUID = Field(foreign_key="users.id", index=True)

    status: FollowUpRoomStatus = Field(default=FollowUpRoomStatus.active, index=True)
    last_message_at: Optional[datetime] = Field(default=None, index=True)

    # The appointment (session) where this follow-up was created
    created_from_appointment_id: Optional[uuid.UUID] = Field(
        default=None, foreign_key="appointments.id", index=True
    )

    # Cancellation tracking — either party can cancel
    cancelled_by_user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id")
    cancelled_at: Optional[datetime] = Field(default=None)

    # Reactivation — set when a closed room is reopened
    reactivated_at: Optional[datetime] = Field(default=None)

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class FollowUpMessage(SQLModel, table=True):
    __tablename__ = "followup_messages"

    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    room_id: uuid.UUID = Field(foreign_key="followup_rooms.id", index=True)
    sender_user_id: uuid.UUID = Field(foreign_key="users.id", index=True)

    message: str
    # System messages (proposal events) are flagged so UI can style them differently
    is_system: bool = Field(default=False, index=True)
    sent_at: datetime = Field(default_factory=utc_now, index=True)


class TimeProposal(SQLModel, table=True):
    __tablename__ = "time_proposals"

    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    room_id: uuid.UUID = Field(foreign_key="followup_rooms.id", index=True)

    proposed_by_user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    start_at: datetime = Field(index=True)
    end_at: datetime = Field(index=True)

    status: ProposalStatus = Field(default=ProposalStatus.pending, index=True)
    responded_by_user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id")
    responded_at: Optional[datetime] = Field(default=None)

    # Filled in when accepted and an appointment is created
    appointment_id: Optional[uuid.UUID] = Field(default=None, foreign_key="appointments.id")

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


# ─── Response / Request schemas ────────────────────────────────────────────────

class FollowUpRoomRead(SQLModel):
    id: uuid.UUID
    user_id: uuid.UUID
    consultant_user_id: uuid.UUID
    status: FollowUpRoomStatus
    last_message_at: Optional[datetime] = None
    created_from_appointment_id: Optional[uuid.UUID] = None
    cancelled_by_user_id: Optional[uuid.UUID] = None
    cancelled_at: Optional[datetime] = None
    reactivated_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    # Populated by service for list/detail views
    other_party_name: Optional[str] = None
    other_party_email: Optional[str] = None
    cancelled_by_name: Optional[str] = None  # human-readable who cancelled


class FollowUpMessageRead(SQLModel):
    id: uuid.UUID
    room_id: uuid.UUID
    sender_user_id: uuid.UUID
    message: str
    is_system: bool
    sent_at: datetime


class TimeProposalRead(SQLModel):
    id: uuid.UUID
    room_id: uuid.UUID
    proposed_by_user_id: uuid.UUID
    start_at: datetime
    end_at: datetime
    status: ProposalStatus
    responded_by_user_id: Optional[uuid.UUID] = None
    responded_at: Optional[datetime] = None
    appointment_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime


class CreateRoomRequest(SQLModel):
    """Consultant or user can initiate a follow-up room with the other party."""
    other_user_id: uuid.UUID


class SendMessageRequest(SQLModel):
    message: str


class CreateProposalRequest(SQLModel):
    start_at: datetime
    end_at: datetime
