import datetime as _dt
from datetime import datetime, date
from enum import Enum
from typing import List, Optional
import uuid

from pydantic import EmailStr, field_validator
from sqlmodel import SQLModel, Field

from app.utils.time import utc_now


def normalize_days_of_week(v):
    """Coerce a weekday schedule to sorted unique ints in 0-6 (Mon=0 … Sun=6).
    Empty / all-invalid → None, meaning 'every day'."""
    if v is None:
        return None
    try:
        days = sorted({int(d) for d in v if 0 <= int(d) <= 6})
    except (TypeError, ValueError):
        return None
    return days or None


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


class MilestoneType(str, Enum):
    """Long-term, non-destructive aim. Richer than GoalType; maps down to a
    GoalType for the macro pipeline (see user_goal_service)."""
    lose_weight = "lose_weight"
    gain_weight = "gain_weight"
    gain_muscle = "gain_muscle"
    maintain = "maintain"


class DailyGoalType(str, Enum):
    """A daily habit that drives a milestone."""
    exercise = "exercise"
    calorie_burn = "calorie_burn"
    intake = "intake"
    steps = "steps"
    custom = "custom"


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


# ── Milestone <-> GoalType mapping ──────────────────────────────────────────

_MILESTONE_TO_GOAL = {
    MilestoneType.lose_weight: GoalType.lose,
    MilestoneType.gain_weight: GoalType.gain,
    MilestoneType.gain_muscle: GoalType.gain,
    MilestoneType.maintain: GoalType.maintain,
}


def goal_type_for_milestone(milestone_type: Optional[MilestoneType]) -> Optional[GoalType]:
    """Map the richer milestone_type down to the GoalType the macro pipeline uses."""
    if milestone_type is None:
        return None
    return _MILESTONE_TO_GOAL.get(milestone_type)


# ── Dynamic `attributes` validation (per type) ──────────────────────────────
# Core, queryable data lives in columns; these validate the free-form JSON shape
# so it doesn't drift. Extra keys are allowed; known keys are type-checked.

class _AttrBase(SQLModel):
    class Config:
        extra = "allow"


class ExerciseAttrs(_AttrBase):
    exercise: Optional[str] = None
    reps: Optional[int] = None
    sets: Optional[int] = None
    duration_min: Optional[float] = None


class CalorieBurnAttrs(_AttrBase):
    kcal: Optional[float] = None


class IntakeAttrs(_AttrBase):
    item: Optional[str] = None
    amount: Optional[float] = None


class StepsAttrs(_AttrBase):
    steps: Optional[int] = None


_DAILY_ATTR_MODELS = {
    DailyGoalType.exercise: ExerciseAttrs,
    DailyGoalType.calorie_burn: CalorieBurnAttrs,
    DailyGoalType.intake: IntakeAttrs,
    DailyGoalType.steps: StepsAttrs,
    DailyGoalType.custom: _AttrBase,
}


def validate_daily_goal_attributes(goal_type: DailyGoalType, attributes: Optional[dict]) -> dict:
    """Validate + normalize the JSON attributes for a daily goal. Raises ValueError."""
    model = _DAILY_ATTR_MODELS.get(goal_type, _AttrBase)
    return model.model_validate(attributes or {}).model_dump(exclude_none=True)


def validate_milestone_attributes(milestone_type: Optional[MilestoneType], attributes: Optional[dict]) -> dict:
    """Milestone attributes are free-form for now; validate it is a JSON object."""
    if attributes is None:
        return {}
    if not isinstance(attributes, dict):
        raise ValueError("attributes must be a JSON object")
    return attributes


# ── Daily goal schemas ──────────────────────────────────────────────────────

class DailyGoalCreate(SQLModel):
    goal_type: DailyGoalType
    name: str
    target_value: Optional[float] = None
    unit: Optional[str] = None
    active: bool = True
    milestone_id: Optional[uuid.UUID] = None
    days_of_week: Optional[List[int]] = None   # Mon=0 … Sun=6; None/[] = every day
    attributes: dict = {}

    _norm_days = field_validator("days_of_week")(lambda cls, v: normalize_days_of_week(v))


class DailyGoalUpdate(SQLModel):
    goal_type: Optional[DailyGoalType] = None
    name: Optional[str] = None
    target_value: Optional[float] = None
    unit: Optional[str] = None
    active: Optional[bool] = None
    milestone_id: Optional[uuid.UUID] = None
    days_of_week: Optional[List[int]] = None
    attributes: Optional[dict] = None

    _norm_days = field_validator("days_of_week")(lambda cls, v: normalize_days_of_week(v))


class DailyGoalRead(SQLModel):
    id: uuid.UUID
    created_for: uuid.UUID
    milestone_id: Optional[uuid.UUID] = None
    goal_type: DailyGoalType
    name: str
    target_value: Optional[float] = None
    unit: Optional[str] = None
    active: bool
    days_of_week: Optional[List[int]] = None
    attributes: dict = {}
    created_at: datetime
    updated_at: datetime


class DailyGoalCompletion(SQLModel):
    daily_goal_id: uuid.UUID
    completed: bool = False
    value: Optional[float] = None


class DailyLogSubmit(SQLModel):
    # NB: use the module-qualified type — a field named `date` would otherwise
    # shadow the `date` type and resolve the annotation to NoneType.
    date: Optional[_dt.date] = None                   # client local date; defaults to today
    completions: List[DailyGoalCompletion] = []
    calories_in: Optional[float] = None
    calories_out: Optional[float] = None
