from __future__ import annotations

from datetime import datetime
from typing import Optional
import uuid

from sqlmodel import SQLModel

from app.modules.appointment.models.appointment import (
    AppointmentBase,
    Appointment,
    SessionStatus,
    FollowUpRoomStatus,
    ProposalStatus,
)
from app.modules.user.schemas import UserRead
from app.modules.user.models import UserData as UserDataRead
from app.modules.milestone.models import Milestone
from app.modules.nutrition_target.models import NutritionTarget
from app.modules.meal_plan_setting.schemas import MealPlanSettingRead


# ── Appointment schemas ────────────────────────────────────────────────────

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


class AppointmentDetailsResponse(SQLModel):
    appointment: Appointment
    goal: Optional[Milestone] = None
    nutrition_target: Optional[NutritionTarget] = None
    meal_plan_setting: Optional[MealPlanSettingRead] = None
    consultant: Optional[UserRead] = None


# ── Follow-up schemas ──────────────────────────────────────────────────────

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


class SendMessageRequest(SQLModel):
    message: str


class CreateProposalRequest(SQLModel):
    start_at: datetime
    end_at: datetime
