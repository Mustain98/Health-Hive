from __future__ import annotations

from typing import List, Optional
from datetime import datetime
from sqlmodel import SQLModel

from app.models.consultant_access import PermissionScope, PermissionStatus


class ConsultantPermissionBase(SQLModel):
    scope: PermissionScope
    resources: List[str]


class ConsultantPermissionCreate(ConsultantPermissionBase):
    pass


class ConsultantPermissionUpdate(SQLModel):
    scope: Optional[PermissionScope] = None
    resources: Optional[List[str]] = None


class ConsultantPermissionRead(ConsultantPermissionBase):
    id: int
    user_id: int
    consultant_user_id: int
    status: PermissionStatus
    granted_in_appointment_id: Optional[int]
    
    granted_at: datetime
    revoked_at: Optional[datetime] = None
    created_at: datetime
