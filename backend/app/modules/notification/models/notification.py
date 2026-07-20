from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
import uuid

from sqlalchemy import JSON, Column
from sqlmodel import SQLModel, Field

from app.utils.time import utc_now


class NotificationType(str, Enum):
    setup_ready = "setup_ready"          # chatbot drafts ready to review/activate
    daily_log = "daily_log"              # "log your day" prompt
    consult_referral = "consult_referral"  # risky case → see a consultant
    generic = "generic"


class Notification(SQLModel, table=True):
    __tablename__ = "notifications"

    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    type: NotificationType = Field(default=NotificationType.generic, index=True)
    title: str
    body: Optional[str] = None
    # Free-form payload (e.g. draft ids to open, deep-link target). Stored as JSON.
    data: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False, server_default="{}"))
    read: bool = Field(default=False, index=True)
    created_at: datetime = Field(default_factory=utc_now, index=True)
