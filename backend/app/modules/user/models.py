from datetime import datetime, date
from typing import List, Optional
import uuid

from pydantic import EmailStr
from sqlalchemy import JSON, Column
from sqlmodel import SQLModel, Field

from app.utils.time import utc_now

# Re-export enums + schemas so `from app.modules.user.models import X` keeps working
from .schemas import *  # noqa: F401,F403
from .schemas import UserType, Gender, ActivityLevel, GoalType, DietPreference, HealthCondition


# ── User / auth ────────────────────────────────────────────────────────────

class User(SQLModel, table=True):
    __tablename__ = "users"
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    email: EmailStr = Field(unique=True, index=True)
    username: str = Field(unique=True, index=True)
    full_name: Optional[str] = None
    user_type: UserType = Field(default=UserType.user)
    hashed_password: str


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


class UserGoalLog(SQLModel, table=True):
    __tablename__ = "user_goal_logs"
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    goal_id: uuid.UUID = Field(foreign_key="user_goals.id", index=True)
    date: datetime = Field(default_factory=utc_now)
    weight: float = Field(nullable=False)
    due_terget: float = Field(default=0.0)


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


# ── Goals ──────────────────────────────────────────────────────────────────

class UserGoal(SQLModel, table=True):
    __tablename__ = "user_goals"

    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    created_for: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id", index=True)
    created_by: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id", index=True)
    appointment_id: Optional[uuid.UUID] = Field(default=None, foreign_key="appointments.id", index=True)
    goal_type: GoalType
    target_weight: Optional[float] = Field(default=None, gt=0)      # Absolute target weight in kg
    initial_weight: Optional[float] = Field(default=None, gt=0)     # Weight at time of activation
    duration_days: Optional[int] = Field(default=None, gt=0)
    active: bool = Field(default=False, nullable=False)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


# ── Nutrition targets ──────────────────────────────────────────────────────

class NutritionTarget(SQLModel, table=True):
    __tablename__ = "nutrition_targets"

    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    created_for: uuid.UUID = Field(foreign_key="users.id", index=True)
    created_by: uuid.UUID = Field(foreign_key="users.id", index=True)
    appointment_id: Optional[uuid.UUID] = Field(foreign_key="appointments.id", default=None, index=True)
    active: bool = Field(default=False, nullable=False)
    calories_kcal: int = Field(ge=800, le=10000)
    protein_g: float = Field(ge=0, le=400)
    carbs_g: float = Field(ge=0, le=1200)
    fat_g: float = Field(ge=0, le=300)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


# ── Health & dietary profile ───────────────────────────────────────────────

class UserHealthProfile(SQLModel, table=True):
    __tablename__ = "user_health_profile"

    user_id: uuid.UUID = Field(foreign_key="users.id", primary_key=True)
    diet_preferences: List[DietPreference] = Field(default=[], sa_column=Column(JSON, nullable=False, default=[]))
    health_conditions: List[HealthCondition] = Field(default=[], sa_column=Column(JSON, nullable=False, default=[]))
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
