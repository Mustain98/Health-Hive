"""Setup-chatbot persistence: a back-and-forth session where the user shapes their
milestone / nutrition requirement / meal setting with an LLM. On finalize the LLM
emits INACTIVE drafts the user reviews and activates separately.

Mirrors the consultation chat pattern (session + messages + status).
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional
import uuid

from sqlalchemy import Column, JSON
from sqlmodel import SQLModel, Field

from app.utils.time import utc_now

# Hard ceiling on one chat session. This used to be 20 and doubled as the context
# limit: hitting it closed the session and forced the user to start over. The agent
# now runs SummarizationMiddleware, which compresses older turns so a long chat keeps
# working, so this is purely a cost/abuse ceiling and should rarely be reached.
MAX_MESSAGES = 200


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
    # "Ask before saving": when true, every write tool pauses for the user's
    # approve/edit/reject decision (human-in-the-loop). Per-session, user-toggled;
    # SETUP_CHAT_HITL only seeds the default for new sessions.
    approval_mode: bool = Field(default=True, nullable=False)
    # The LangGraph thread id awaiting the user's decisions (None = nothing pending). A new
    # user message abandons any stale proposal by clearing this — nothing was written,
    # so there is nothing to undo.
    pending_thread_id: Optional[str] = Field(default=None, index=True)
    # Short rolling-memory summary, written when the session finalizes/closes.
    summary: Optional[str] = Field(default=None)

    # Cumulative LLM token usage for this chat, recorded by TokenUsageMiddleware.
    # Purpose is measurement: MAX_MESSAGES and the summarization trigger are currently
    # guesses, and these columns are the data needed to replace them with token budgets.
    total_input_tokens: int = Field(default=0, nullable=False)
    total_output_tokens: int = Field(default=0, nullable=False)
    llm_call_count: int = Field(default=0, nullable=False)

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class PlanSetupMessage(SQLModel, table=True):
    __tablename__ = "plan_setup_messages"

    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    session_id: uuid.UUID = Field(foreign_key="plan_setup_sessions.id", index=True)
    role: SetupRole
    content: str
    created_at: datetime = Field(default_factory=utc_now, index=True)


class PlanProposal(SQLModel, table=True):
    """RETIRED — no code reads or writes this table.

    It used to stage a proposed batch between the agent proposing and the user deciding,
    so nine habits proposed across nine model calls still arrived as ONE approval card.
    LangGraph's checkpointer now holds the suspended run (`hitl.py`) and carries the whole
    batch with it, which made the staging layer redundant; its service functions were
    removed from `proposal.py`, leaving only the validation half.

    The class is kept ONLY so SQLModel's metadata still matches the live schema — Alembic
    0017 created `plan_proposals`, and startup calls `create_db_and_tables()`. Dropping it
    needs a migration, not just deleting this class.

    How dead it was: the removed staging code assigned `setup_session.pending_proposal_id`,
    a field 0017 added to the table but which no longer exists on `PlanSetupSession` — so
    it would have raised AttributeError had anything called it. A migration that drops this
    table should drop that column too.
    """
    __tablename__ = "plan_proposals"

    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    session_id: uuid.UUID = Field(foreign_key="plan_setup_sessions.id", index=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    items: list[Any] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    resolved_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now, index=True)
