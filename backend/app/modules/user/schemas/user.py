import datetime as _dt
from datetime import datetime
from enum import Enum
from typing import List, Optional
import uuid

from pydantic import EmailStr
from sqlmodel import SQLModel


# ── Enums ──────────────────────────────────────────────────────────────────

class UserType(str, Enum):
    user = "user"
    consultant = "consultant"
    admin = "admin"


class Gender(str, Enum):
    male = "male"
    female = "female"


class ActivityLevel(str, Enum):
    sedentary = "sedentary"
    light = "light"
    moderate = "moderate"
    active = "active"
    very_active = "very_active"


class DietPreference(str, Enum):
    none = "none"
    vegetarian = "vegetarian"
    vegan = "vegan"
    halal = "halal"
    kosher = "kosher"
    pescatarian = "pescatarian"


class HealthCondition(str, Enum):
    hypertension = "hypertension"
    diabetes = "diabetes"
    high_cholesterol = "high_cholesterol"
    heart_disease = "heart_disease"
    kidney_disease = "kidney_disease"
    obesity = "obesity"
    other = "other"


# ── Auth / User schemas ────────────────────────────────────────────────────

class Token(SQLModel):
    access_token: str
    token_type: str


class UserLogin(SQLModel):
    identifier: str
    password: str


class UserRegister(SQLModel):
    username: Optional[str] = None
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class UserPasswordUpdate(SQLModel):
    old_password: str
    new_password: str


class UserRead(SQLModel):
    id: uuid.UUID
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    user_type: UserType


class UserUpdate(SQLModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None


# ── health profile schemas ─────────────────────────────────────────────────

class UserHealthProfileUpsert(SQLModel):
    diet_preferences: List[DietPreference] = []
    health_conditions: List[HealthCondition] = []
    notes: Optional[str] = None


class UserHealthProfileRead(SQLModel):
    user_id: uuid.UUID
    diet_preferences: List[DietPreference] = []
    health_conditions: List[HealthCondition] = []
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# DailyLogSubmit moved to app.modules.daily_log.schemas; re-exported above.
