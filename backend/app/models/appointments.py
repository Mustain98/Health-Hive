from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import SQLModel, Field

from app.models.user_data import utc_now


class ApplicationStatus(str, Enum):
    submitted = "submitted"
    rejected = "rejected"
    accepted = "accepted"
    cancelled = "cancelled"


class AppointmentStatus(str, Enum):
    scheduled = "scheduled"
    completed = "completed"
    cancelled = "cancelled"
    no_show = "no_show"


# ✅ NEW: session lifecycle states
class SessionStatus(str, Enum):
    not_started = "not_started"
    active = "active"
    ended = "ended"


class AppointmentApplication(SQLModel, table=True):
    __tablename__ = "appointment_applications"

    id: Optional[int] = Field(default=None, primary_key=True, index=True)

    user_id: int = Field(foreign_key="users.id", index=True)  # client
    consultant_user_id: int = Field(foreign_key="users.id", index=True)

    note_from_user: Optional[str] = None

    status: ApplicationStatus = Field(default=ApplicationStatus.submitted, index=True)

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class Appointment(SQLModel, table=True):
    __tablename__ = "appointments"

    id: Optional[int] = Field(default=None, primary_key=True, index=True)

    application_id: Optional[int] = Field(
        default=None,
        foreign_key="appointment_applications.id",
        index=True,
    )

    user_id: int = Field(foreign_key="users.id", index=True)
    consultant_user_id: int = Field(foreign_key="users.id", index=True)

    scheduled_start_at: datetime = Field(index=True)
    scheduled_end_at: datetime

    status: AppointmentStatus = Field(default=AppointmentStatus.scheduled, index=True)

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class SessionRoom(SQLModel, table=True):
    __tablename__ = "session_rooms"

    id: Optional[int] = Field(default=None, primary_key=True, index=True)

    appointment_id: int = Field(
        foreign_key="appointments.id",
        index=True,
        unique=True,
    )

    # ✅ default is NOT_STARTED (user can't enter)
    status: SessionStatus = Field(default=SessionStatus.not_started, index=True)

    # ✅ consultant-controlled lifecycle
    started_at: Optional[datetime] = Field(default=None, index=True)
    ended_at: Optional[datetime] = Field(default=None, index=True)

    started_by_user_id: Optional[int] = Field(default=None, foreign_key="users.id", index=True)
    ended_by_user_id: Optional[int] = Field(default=None, foreign_key="users.id", index=True)

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ChatMessage(SQLModel, table=True):
    __tablename__ = "chat_messages"

    id: Optional[int] = Field(default=None, primary_key=True, index=True)

    room_id: int = Field(foreign_key="session_rooms.id", index=True)
    sender_user_id: int = Field(foreign_key="users.id", index=True)

    message: str
    sent_at: datetime = Field(default_factory=utc_now, index=True)


class SessionNote(SQLModel, table=True):
    __tablename__ = "session_notes"

    id: Optional[int] = Field(default=None, primary_key=True, index=True)

    appointment_id: int = Field(
        foreign_key="appointments.id",
        index=True,
        unique=True,
    )
    created_by_user_id: int = Field(foreign_key="users.id", index=True)

    note: str
    is_visible_to_user: bool = Field(default=False, index=True)

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
