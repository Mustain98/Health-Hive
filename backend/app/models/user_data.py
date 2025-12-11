from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlmodel import SQLModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Gender(str, Enum):
    male = "male"
    female = "female"


class ActivityLevel(str, Enum):
    sedentary = "sedentary"
    light = "light"
    moderate = "moderate"
    active = "active"
    very_active = "very_active"


class UserDataBase(SQLModel):
    age: Optional[int] = Field(default=None, ge=10, le=120)
    gender: Optional[Gender] = None   # 👈 now enum

    height_cm: Optional[float] = Field(default=None, ge=50, le=260)
    weight_kg: Optional[float] = Field(default=None, ge=20, le=400)

    activity_level: Optional[ActivityLevel] = None


class UserData(UserDataBase, table=True):
    __tablename__ = "user_data"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
