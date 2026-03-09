from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ReportCreate(BaseModel):
    type: str
    content_id: str
    content_preview: str
    reported_user_id: str
    severity: Optional[str] = "medium"


class ReportResponse(BaseModel):
    id: str
    type: str
    content_id: str
    content_preview: str
    reporter_id: str
    reported_user_id: str
    severity: str
    status: str
    created_at: datetime
    reporter_name: Optional[str] = None
    reported_name: Optional[str] = None


class ReportActionRequest(BaseModel):
    action: str          # "remove" | "warn" | "ban" | "dismiss" | "resolve"
    note: Optional[str] = None


class VerifyConsultantRequest(BaseModel):
    decision: str        # "approve" | "reject"
    note: Optional[str] = None


class UserStatusRequest(BaseModel):
    status: str          # "active" | "banned"
    note: Optional[str] = None