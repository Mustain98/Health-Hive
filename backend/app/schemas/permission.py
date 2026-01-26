from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlmodel import SQLModel

from app.models.consultant_access import PermissionScope, PermissionStatus, AuditResource, AuditAction


class PermissionGrant(SQLModel):
    consultant_user_id: int
    scope: PermissionScope = PermissionScope.read
    resources: List[str]
    granted_in_appointment_id: Optional[int] = None


class PermissionRead(SQLModel):
    id: int
    user_id: int
    consultant_user_id: int
    scope: PermissionScope
    resources: List[str]
    status: PermissionStatus
    granted_at: datetime
    revoked_at: Optional[datetime] = None
    granted_in_appointment_id: Optional[int] = None
    created_at: datetime


class PermissionRevoke(SQLModel):
    consultant_user_id: int


class UserHealthChangeAuditRead(SQLModel):
    id: int
    user_id: int
    changed_by_user_id: int
    resource: AuditResource
    action: AuditAction
    before_json: Optional[str] = None
    after_json: Optional[str] = None
    appointment_id: Optional[int] = None
    created_at: datetime
