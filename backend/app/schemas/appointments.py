from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import SQLModel
from app.schemas.user import UserRead


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


# ✅ NEW: real session lifecycle
class SessionStatus(str, Enum):
    not_started = "not_started"
    active = "active"
    ended = "ended"


class AppointmentApplicationCreate(SQLModel):
    consultant_user_id: int
    note_from_user: Optional[str] = None


class AppointmentApplicationRead(SQLModel):
    id: int
    user_id: int
    consultant_user_id: int
    note_from_user: Optional[str] = None
    status: ApplicationStatus
    created_at: datetime
    updated_at: datetime


class AppointmentDecision(SQLModel):
    # consultant decision on application
    status: ApplicationStatus  # accepted/rejected/cancelled


class AppointmentSchedule(SQLModel):
    scheduled_start_at: datetime
    scheduled_end_at: datetime


class AppointmentCreateFromApplication(SQLModel):
    application_id: int
    scheduled_start_at: datetime
    scheduled_end_at: datetime



class AppointmentRead(SQLModel):
    id: int
    application_id: Optional[int] = None
    user_id: int
    consultant_user_id: int
    scheduled_start_at: datetime
    scheduled_end_at: datetime
    status: AppointmentStatus
    created_at: datetime
    updated_at: datetime



from app.schemas.user_data import UserDataRead

class AppointmentReadWithUser(AppointmentRead):
    user: UserRead
    user_data: Optional[UserDataRead] = None
    session_status: Optional[SessionStatus] = None



# ✅ UPDATED: session room state + lifecycle metadata
class SessionRoomRead(SQLModel):
    id: int
    appointment_id: int

    status: SessionStatus

    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

    started_by_user_id: Optional[int] = None
    ended_by_user_id: Optional[int] = None

    created_at: datetime
    updated_at: datetime


class ChatMessageCreate(SQLModel):
    message: str


class ChatMessageRead(SQLModel):
    id: int
    room_id: int
    sender_user_id: int
    message: str
    sent_at: datetime


class SessionNoteCreate(SQLModel):
    note: str
    is_visible_to_user: bool = False


class SessionNoteUpdate(SQLModel):
    note: Optional[str] = None
    is_visible_to_user: Optional[bool] = None


class SessionNoteRead(SQLModel):
    id: int
    appointment_id: int
    created_by_user_id: int
    note: str
    is_visible_to_user: bool
    created_at: datetime
    updated_at: datetime
