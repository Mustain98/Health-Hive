from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional, List

from sqlmodel import SQLModel, Field
from sqlalchemy import Column
from sqlalchemy.types import JSON

from app.models.user_data import utc_now


class PermissionScope(str, Enum):
    read = "read"
    read_write = "read_write"


class PermissionStatus(str, Enum):
    active = "active"
    revoked = "revoked"


class AuditResource(str, Enum):
    nutrition_targets = "nutrition_targets"
    user_goals = "user_goals"
    user_data = "user_data"


class AuditAction(str, Enum):
    create = "create"
    update = "update"
    delete = "delete"


class ConsultantPermission(SQLModel, table=True):
    __tablename__ = "consultant_permissions"

    id: Optional[int] = Field(default=None, primary_key=True, index=True)

    user_id: int = Field(foreign_key="users.id", index=True)
    consultant_user_id: int = Field(foreign_key="users.id", index=True)

    scope: PermissionScope = Field(index=True)
    resources: List[str] = Field(sa_column=Column(JSON))

    status: PermissionStatus = Field(default=PermissionStatus.active, index=True)

    # Session-scoped: tied to specific appointment
    granted_in_appointment_id: Optional[int] = Field(default=None, foreign_key="appointments.id", index=True)

    granted_at: datetime = Field(default_factory=utc_now)
    revoked_at: Optional[datetime] = None

    created_at: datetime = Field(default_factory=utc_now)


class UserHealthChangeAudit(SQLModel, table=True):
    __tablename__ = "user_health_change_audit"

    id: Optional[int] = Field(default=None, primary_key=True, index=True)

    user_id: int = Field(foreign_key="users.id", index=True)
    changed_by_user_id: int = Field(foreign_key="users.id", index=True)

    resource: AuditResource = Field(index=True)
    action: AuditAction = Field(index=True)

    before_json: Optional[str] = None
    after_json: Optional[str] = None

    appointment_id: Optional[int] = Field(default=None, foreign_key="appointments.id", index=True)

    created_at: datetime = Field(default_factory=utc_now, index=True)
