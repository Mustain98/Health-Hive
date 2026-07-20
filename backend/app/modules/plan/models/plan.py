from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
import uuid

from sqlalchemy import Column
from sqlalchemy import Enum as SAEnum
from sqlmodel import SQLModel, Field

from app.utils.time import utc_now


class PlanSource(str, Enum):
    self_ = "self"          # the user built it
    ai = "ai"               # the setup chatbot generated it
    consultant = "consultant"  # a consultant created it


class Plan(SQLModel, table=True):
    """Groups a milestone + daily goals + nutrition requirement + meal setting
    into ONE plan, activated as a unit (one active plan per user). The four parts
    reference this via their `plan_id`."""
    __tablename__ = "plans"

    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    created_for: uuid.UUID = Field(foreign_key="users.id", index=True)
    created_by: uuid.UUID = Field(foreign_key="users.id", index=True)
    name: str = Field(default="My Plan", max_length=255)
    # Store the enum VALUE ("self"/"ai"/"consultant"), not the member name ("self_").
    source: PlanSource = Field(
        default=PlanSource.self_,
        sa_column=Column(
            SAEnum(PlanSource, native_enum=False, values_callable=lambda e: [m.value for m in e]),
            nullable=False, index=True, server_default="self",
        ),
    )
    active: bool = Field(default=False, nullable=False)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

