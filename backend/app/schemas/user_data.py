from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel

from app.models.user_data import ActivityLevel, Gender


class UserDataBaseSchema(SQLModel):
    age: Optional[int] = None
    gender: Optional[Gender] = None   # 👈 enum here as well

    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None

    activity_level: Optional[ActivityLevel] = None


class UserDataCreate(UserDataBaseSchema):
    """Data user can first input after registering."""
    pass


class UserDataUpdate(UserDataBaseSchema):
    """Same fields, all optional for partial updates."""
    pass


class UserDataRead(UserDataBaseSchema):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    pass