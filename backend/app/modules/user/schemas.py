from datetime import datetime, date
from enum import Enum
from typing import List, Optional
import uuid

from pydantic import EmailStr
from sqlmodel import SQLModel, Field

from app.utils.time import utc_now


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


class GoalType(str, Enum):
    lose = "lose"
    gain = "gain"
    maintain = "maintain"


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


# ── user_data schemas ──────────────────────────────────────────────────────

class UserGoalLogCreate(SQLModel):
    weight: float
    date: Optional[datetime] = None  # defaults to today in service


# ── goal schemas ───────────────────────────────────────────────────────────

class UserGoalUpdate(SQLModel):
    active: bool = Field(default_factory=False, nullable=False)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    updated_at: Optional[datetime] = utc_now


class GoalDateChangeRequest(SQLModel):
    new_start_date: date


# ── nutrition target schemas ───────────────────────────────────────────────

class NutritionTargetUpdate(SQLModel):
    calories_kcal: Optional[int] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    active: bool = False


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
