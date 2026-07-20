from datetime import datetime
from typing import Optional
import uuid

from sqlmodel import SQLModel


class NotificationRead(SQLModel):
    id: uuid.UUID
    type: str
    title: str
    body: Optional[str] = None
    data: dict = {}
    read: bool
    created_at: datetime


class UnreadCount(SQLModel):
    unread: int
