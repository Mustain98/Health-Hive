from datetime import datetime
from typing import List, Optional
import uuid

from pydantic import EmailStr
from sqlalchemy import JSON, Column
from sqlmodel import SQLModel, Field

from app.utils.time import utc_now

from app.modules.user.schemas import (
    UserType, Gender, ActivityLevel, DietPreference, HealthCondition,
)


# ── User / auth ────────────────────────────────────────────────────────────

class User(SQLModel, table=True):
    __tablename__ = "users"
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    email: EmailStr = Field(unique=True, index=True)
    username: str = Field(unique=True, index=True)
    full_name: Optional[str] = None
    user_type: UserType = Field(default=UserType.user)
    hashed_password: str
    # False for accounts created via Google (they hold only a random hash) until the
    # user sets a real password. Drives the profile "set" vs "change" password UI.
    has_password: bool = Field(default=True)


# ── User data / logs ───────────────────────────────────────────────────────

class UserData(SQLModel, table=True):
    __tablename__ = "user_data"

    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    age: Optional[int] = Field(default=None, ge=10, le=120)
    gender: Optional[Gender] = None

    height_cm: Optional[float] = Field(default=None, ge=50, le=260)
    weight_kg: Optional[float] = Field(default=None, ge=20, le=400)

    activity_level: Optional[ActivityLevel] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class UserAllergen(SQLModel, table=True):
    __tablename__ = "user_allergen"

    user_id: uuid.UUID = Field(foreign_key="users.id", primary_key=True)
    food_item_id: uuid.UUID = Field(foreign_key="food_item.id", primary_key=True)

    created_at: datetime = Field(default_factory=utc_now)


class UserPreference(SQLModel, table=True):
    __tablename__ = "user_preference"

    user_id: uuid.UUID = Field(foreign_key="users.id", primary_key=True)
    food_item_id: uuid.UUID = Field(foreign_key="food_item.id", primary_key=True)

    created_at: datetime = Field(default_factory=utc_now)


# DailyLog moved to app.modules.daily_log.models (table `daily_logs` unchanged);
# re-exported above for back-compat.


# ── Health & dietary profile ───────────────────────────────────────────────

class UserHealthProfile(SQLModel, table=True):
    __tablename__ = "user_health_profile"

    user_id: uuid.UUID = Field(foreign_key="users.id", primary_key=True)
    diet_preferences: List[DietPreference] = Field(default=[], sa_column=Column(JSON, nullable=False, default=[]))
    health_conditions: List[HealthCondition] = Field(default=[], sa_column=Column(JSON, nullable=False, default=[]))
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
