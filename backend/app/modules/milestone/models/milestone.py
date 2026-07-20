"""Milestone tables.

`__tablename__` values are unchanged from when these lived in `user/models.py`
(`user_goals`) — the move from `user/models.py` needed no data migration.
"""
from datetime import datetime, date
from typing import Optional
import uuid

from sqlalchemy import JSON, Column
from sqlmodel import SQLModel, Field

from app.utils.time import utc_now
from app.core.units import sa_enum
from app.modules.milestone.schemas import GoalType, MilestoneType, MilestoneUnit


class Milestone(SQLModel, table=True):
    """A long-term **milestone** (e.g. lose 10 kg in 3 months, +2 kg muscle in
    6 months, maintain weight). `goal_type` is kept for the macro pipeline;
    `milestone_type` is the richer, user-facing type. Variable, non-core detail
    goes in `attributes` (hybrid storage).

    Was `UserGoal`; the table name stays `user_goals` so the rename needed no
    migration."""
    __tablename__ = "user_goals"

    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    created_for: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id", index=True)
    created_by: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id", index=True)
    appointment_id: Optional[uuid.UUID] = Field(default=None, foreign_key="appointments.id", index=True)
    plan_id: Optional[uuid.UUID] = Field(default=None, index=True)  # groups this into a Plan

    goal_type: GoalType                                            # lose/gain/maintain — drives macros
    milestone_type: Optional[MilestoneType] = Field(default=None)  # richer, user-facing type
    name: Optional[str] = Field(default=None, max_length=255)

    target_weight: Optional[float] = Field(default=None, gt=0)      # Absolute target weight in kg
    initial_weight: Optional[float] = Field(default=None, gt=0)     # Weight at time of activation
    target_value: Optional[float] = Field(default=None)            # generic target (e.g. kg of muscle)
    # Closed vocabulary (was free text). VARCHAR + CHECK via native_enum=False.
    unit: Optional[MilestoneUnit] = Field(
        default=None,
        sa_column=Column(sa_enum(MilestoneUnit, name="ck_user_goals_unit"), nullable=True),
    )
    duration_days: Optional[int] = Field(default=None, gt=0)

    active: bool = Field(default=False, nullable=False)
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    # Dynamic, non-core attributes (no fixed schema).
    attributes: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False, server_default="{}"))

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
