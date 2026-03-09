from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
import uuid

from sqlmodel import SQLModel, Field

from app.models.user_data import UserData as UserDataRead
from app.models.user import UserRead
from app.utils.time import utc_now

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
    consultant_access: bool = Field(default=True, index=True) # User can revoke this
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


# --- Schemas ---

class AppointmentApplicationCreate(SQLModel):
    consultant_user_id: uuid.UUID
    requested_start_at: datetime
    note_from_user: Optional[str] = None




class AppointmentDecision(SQLModel):
    # consultant decision on application
    status: ApplicationStatus  # accepted/rejected/cancelled


class AppointmentSchedule(SQLModel):
    scheduled_start_at: datetime
    scheduled_end_at: datetime


class AppointmentCreateFromApplication(SQLModel):
    application_id: uuid.UUID
    scheduled_start_at: datetime
    scheduled_end_at: datetime


class ProposeTimeRequest(SQLModel):
    proposed_start_at: datetime


class FreeWindowResponse(SQLModel):
    start: datetime
    end: datetime




class AppointmentReadWithUser(AppointmentBase):
    id: uuid.UUID 
    user: UserRead
    user_data: Optional[UserDataRead] = None
    session_status: Optional[SessionStatus] = None


class AppointmentWithParticipants(AppointmentBase):
    """Appointment with joined user and consultant display info."""
    id: uuid.UUID
    # User (patient) info
    user_name: Optional[str] = None   # full_name or username
    user_email: Optional[str] = None
    # Consultant info
    consultant_name: Optional[str] = None  # display_name from ConsultantProfile or full_name
    consultant_email: Optional[str] = None
    session_status: Optional[SessionStatus] = None




class ChatMessageCreate(SQLModel):
    message: str




class SessionNoteCreate(SQLModel):
    note: str
    is_visible_to_user: bool = False


class SessionNoteUpdate(SQLModel):
    note: Optional[str] = None
    is_visible_to_user: Optional[bool] = None


from app.models.user_goal import UserGoal
from app.models.nutrition_target import NutritionTarget
from app.models.meal_plan.meal_plan_setting import MealPlanSettingRead

class AppointmentDetailsResponse(SQLModel):
    appointment: Appointment
    goal: Optional[UserGoal] = None
    nutrition_target: Optional[NutritionTarget] = None
    meal_plan_setting: Optional[MealPlanSettingRead] = None
    consultant: Optional[UserRead] = None


