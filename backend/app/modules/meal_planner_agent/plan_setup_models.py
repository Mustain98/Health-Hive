"""Setup-chatbot persistence: a back-and-forth session where the user shapes their
milestone / nutrition requirement / meal setting with an LLM. On finalize the LLM
emits INACTIVE drafts the user reviews and activates separately.

Mirrors the consultation chat pattern (session + messages + status).
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
import uuid

from sqlmodel import SQLModel, Field

from app.utils.time import utc_now

# When a session reaches this many messages, further posting is refused and the
# user is told to open a new session (decision 11 — no force-finalize).
MAX_MESSAGES = 20


class SetupSessionStatus(str, Enum):
    open = "open"
    closed = "closed"


class SetupRole(str, Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


class PlanSetupSession(SQLModel, table=True):
    __tablename__ = "plan_setup_sessions"

    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    status: SetupSessionStatus = Field(default=SetupSessionStatus.open, index=True)
    message_count: int = Field(default=0, nullable=False)
    # The draft Plan this chat is building (parts the agent creates attach here).
    draft_plan_id: Optional[uuid.UUID] = Field(default=None, index=True)
    # Short rolling-memory summary, written when the session finalizes/closes.
    summary: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class PlanSetupMessage(SQLModel, table=True):
    __tablename__ = "plan_setup_messages"

    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    session_id: uuid.UUID = Field(foreign_key="plan_setup_sessions.id", index=True)
    role: SetupRole
    content: str
    created_at: datetime = Field(default_factory=utc_now, index=True)
