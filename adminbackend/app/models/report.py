from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
import uuid


class Report(SQLModel, table=True):
    __tablename__ = "reports"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    type: str                           # "meal_plan" | "message" | "profile"
    content_id: str
    content_preview: str
    reporter_id: str
    reported_user_id: str
    severity: str = "medium"           # "low" | "medium" | "high"
    status: str = "pending"            # "pending" | "actioned" | "dismissed"
    actioned_by: Optional[str] = None
    actioned_at: Optional[datetime] = None
    action_taken: Optional[str] = None
    action_note: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ModerationLog(SQLModel, table=True):
    __tablename__ = "moderation_log"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    admin_id: str
    action: str
    target: str
    note: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)