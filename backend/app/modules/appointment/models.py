from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
import uuid

from sqlmodel import SQLModel, Field

from app.utils.time import utc_now


# ── Enums ──────────────────────────────────────────────────────────────────

class ApplicationStatus(str, Enum):
    submitted = "submitted"                 # user picked requested_start_at
    rejected = "rejected"
    cancelled = "cancelled"

    proposed = "proposed"                   # consultant proposed proposed_start_at
    proposal_accepted = "proposal_accepted" # user accepted proposed_start_at
    scheduled = "scheduled"                 # consultant created Appointment


class AppointmentStatus(str, Enum):
    scheduled = "scheduled"
    completed = "completed"
    cancelled = "cancelled"
    no_show = "no_show"


class SessionStatus(str, Enum):
    not_started = "not_started"
    active = "active"
    ended = "ended"


class FollowUpRoomStatus(str, Enum):
    active = "active"
    closed = "closed"


class ProposalStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"
    cancelled = "cancelled"


# ── Appointment tables ─────────────────────────────────────────────────────

class AppointmentApplication(SQLModel, table=True):
    __tablename__ = "appointment_applications"
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    consultant_user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    note_from_user: Optional[str] = None
    requested_start_at: datetime = Field(index=True, nullable=False)
    proposed_start_at: Optional[datetime] = Field(default=None, index=True)
    proposed_at: Optional[datetime] = None
    proposal_accepted_at: Optional[datetime] = None
    status: ApplicationStatus = Field(default=ApplicationStatus.submitted, index=True)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class AppointmentBase(SQLModel):
    application_id: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="appointment_applications.id",
        index=True,
    )
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    consultant_user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    scheduled_start_at: datetime = Field(index=True)
    scheduled_end_at: datetime = Field(index=True)
    status: AppointmentStatus = Field(default=AppointmentStatus.scheduled, index=True)
    consultant_access: bool = Field(default=True, index=True)  # User can revoke this
    # Links this appointment back to a follow-up room (set by create_followup_from_session
    # and by accept_proposal). Null for appointments created outside a follow-up.
    followup_room_id: Optional[uuid.UUID] = Field(
        default=None, foreign_key="followup_rooms.id", index=True
    )
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class Appointment(AppointmentBase, table=True):
    __tablename__ = "appointments"
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True, index=True)


class SessionRoom(SQLModel, table=True):
    __tablename__ = "session_rooms"
    appointment_id: uuid.UUID = Field(
        foreign_key="appointments.id",
        index=True,
        unique=True,
    )
    status: SessionStatus = Field(default=SessionStatus.not_started, index=True)
    started_at: Optional[datetime] = Field(default=None, index=True)
    ended_at: Optional[datetime] = Field(default=None, index=True)
    started_by_user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id", index=True)
    ended_by_user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id", index=True)

    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ChatMessage(SQLModel, table=True):
    __tablename__ = "chat_messages"
    room_id: uuid.UUID = Field(foreign_key="session_rooms.id", index=True)
    sender_user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    message: str
    sent_at: datetime = Field(default_factory=utc_now, index=True)
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True, index=True)


class SessionNote(SQLModel, table=True):
    __tablename__ = "session_notes"

    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    appointment_id: uuid.UUID = Field(
        foreign_key="appointments.id",
        index=True,
        unique=True,
    )
    created_by_user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    note: str
    is_visible_to_user: bool = Field(default=False, index=True)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


# ── Follow-up tables ───────────────────────────────────────────────────────

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


# Re-export DTO schemas so `from app.modules.appointment.models import X` keeps working.
# Imported last (after all tables/enums/bases are defined) to keep load order safe.
from .schemas import *  # noqa: E402,F401,F403
