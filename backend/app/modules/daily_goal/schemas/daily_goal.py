"""Daily-goal schemas — the habits that drive a milestone.

Units are a closed enum and attributes are typed with `extra="forbid"`, so an LLM
that invents a unit or an attribute key fails at parse time instead of writing it
to the database. Both shapes were sized against the live data (see the audit in
docs/REFACTOR_PLAN.md) — every value present in production validates.
"""
from datetime import datetime
from enum import Enum
from typing import List, Optional
import uuid

from pydantic import ConfigDict, field_validator, model_validator
from sqlmodel import SQLModel, Field


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

class DailyGoalType(str, Enum):
    """A daily habit that drives a milestone."""
    exercise = "exercise"
    calorie_burn = "calorie_burn"
    intake = "intake"
    steps = "steps"
    custom = "custom"


class DailyGoalUnit(str, Enum):
    """Every unit a daily goal may be measured in. Closed on purpose."""
    # duration
    min = "min"
    hr = "hr"
    # count
    reps = "reps"
    sets = "sets"
    steps = "steps"
    times = "times"
    # energy
    kcal = "kcal"
    # mass / volume
    g = "g"
    mg = "mg"
    ml = "ml"
    l = "l"
    # serving
    glasses = "glasses"
    servings = "servings"
    portions = "portions"


# Which units make sense for which goal type. A closed enum alone stops
# "sets of 10-15 reps"; this table additionally stops `steps` on a calorie_burn goal.
# `custom` is deliberately unrestricted — it still must pick from the enum.
_ALLOWED_UNITS: dict[DailyGoalType, set[DailyGoalUnit]] = {
    DailyGoalType.exercise: {
        DailyGoalUnit.min, DailyGoalUnit.hr,
        DailyGoalUnit.reps, DailyGoalUnit.sets,
        DailyGoalUnit.steps,          # "walk 10,000 steps" is a legitimate exercise goal
    },
    DailyGoalType.calorie_burn: {DailyGoalUnit.kcal},
    DailyGoalType.intake: {
        DailyGoalUnit.g, DailyGoalUnit.mg, DailyGoalUnit.ml, DailyGoalUnit.l,
        DailyGoalUnit.kcal, DailyGoalUnit.times,
        DailyGoalUnit.glasses, DailyGoalUnit.servings, DailyGoalUnit.portions,
    },
    DailyGoalType.steps: {DailyGoalUnit.steps},
    DailyGoalType.custom: set(DailyGoalUnit),
}


def validate_unit_for_type(goal_type: Optional[DailyGoalType],
                           unit: Optional[DailyGoalUnit]) -> Optional[DailyGoalUnit]:
    """Reject a unit that is valid in isolation but wrong for this goal type."""
    if unit is None or goal_type is None:
        return unit
    allowed = _ALLOWED_UNITS.get(goal_type, set(DailyGoalUnit))
    if unit not in allowed:
        raise ValueError(
            f"unit '{unit.value}' is not valid for goal_type '{goal_type.value}'. "
            f"Allowed: {sorted(u.value for u in allowed)}"
        )
    return unit


# ── Dynamic `attributes` validation (per type) ─────────────────────────────
# Core, queryable data lives in columns; these pin the free-form JSON shape.
# `extra="forbid"` means a hallucinated key is a parse error, not a stored row.

class _AttrBase(SQLModel):
    model_config = ConfigDict(extra="forbid")


class ExerciseAttrs(_AttrBase):
    exercise: Optional[str] = None
    sets: Optional[int] = Field(default=None, ge=1, le=50)
    reps: Optional[int] = Field(default=None, ge=1, le=1000)
    # Rep ranges ("3 sets of 10-15") — the information the old free-text unit carried.
    reps_min: Optional[int] = Field(default=None, ge=1, le=1000)
    reps_max: Optional[int] = Field(default=None, ge=1, le=1000)
    duration_min: Optional[float] = Field(default=None, ge=0, le=600)
    hold_time_sec: Optional[float] = Field(default=None, ge=0, le=3600)
    per_leg: Optional[bool] = None
    # Derived server-side from sets/reps (or duration). Never sent by the model —
    # see `_derive_total`. Kept here so it round-trips once stored.
    total: Optional[float] = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _check_rep_range(self):
        if self.reps_min is not None and self.reps_max is not None and self.reps_min > self.reps_max:
            raise ValueError("reps_min must be <= reps_max")
        return self


class CalorieBurnAttrs(_AttrBase):
    kcal: Optional[float] = Field(default=None, ge=0, le=10000)


class IntakeAttrs(_AttrBase):
    item: Optional[str] = None
    amount: Optional[float] = Field(default=None, ge=0)


class StepsAttrs(_AttrBase):
    steps: Optional[int] = Field(default=None, ge=0, le=200000)


class CustomAttrs(_AttrBase):
    """Custom goals carry no fixed shape, but still may not invent keys silently."""
    note: Optional[str] = None
    amount: Optional[float] = None


_DAILY_ATTR_MODELS = {
    DailyGoalType.exercise: ExerciseAttrs,
    DailyGoalType.calorie_burn: CalorieBurnAttrs,
    DailyGoalType.intake: IntakeAttrs,
    DailyGoalType.steps: StepsAttrs,
    DailyGoalType.custom: CustomAttrs,
}


def _derive_total(goal_type: DailyGoalType, data: dict) -> dict:
    """Compute `total` from the parts rather than trusting the model's arithmetic.

    Mirrors the "LLM thinks / code decides" split already used in meal planning:
    the model supplies sets/reps/duration, the server multiplies.
    """
    if goal_type is not DailyGoalType.exercise:
        return data
    sets, reps = data.get("sets"), data.get("reps")
    if sets is not None and reps is not None:
        data["total"] = float(sets) * float(reps)
    elif sets is not None and data.get("reps_max") is not None:
        data["total"] = float(sets) * float(data["reps_max"])
    elif data.get("duration_min") is not None:
        data["total"] = float(data["duration_min"])
    else:
        data.pop("total", None)
    return data


def validate_daily_goal_attributes(goal_type: DailyGoalType, attributes: Optional[dict]) -> dict:
    """Validate + normalize the JSON attributes for a daily goal. Raises ValueError.

    Unknown keys are rejected (`extra="forbid"`), numeric bounds are enforced, and
    `total` is recomputed server-side from whatever the caller supplied.
    """
    model = _DAILY_ATTR_MODELS.get(goal_type, CustomAttrs)
    incoming = dict(attributes or {})
    incoming.pop("total", None)          # never trust a supplied total
    data = model.model_validate(incoming).model_dump(exclude_none=True)
    return _derive_total(goal_type, data)


# ── Schemas ────────────────────────────────────────────────────────────────

class DailyGoalCreate(SQLModel):
    goal_type: DailyGoalType
    name: str
    target_value: Optional[float] = None
    unit: Optional[DailyGoalUnit] = None
    active: bool = True
    milestone_id: Optional[uuid.UUID] = None
    days_of_week: Optional[List[int]] = None   # Mon=0 … Sun=6; None/[] = every day
    attributes: dict = {}

    _norm_days = field_validator("days_of_week")(lambda cls, v: normalize_days_of_week(v))

    @model_validator(mode="after")
    def _check_unit(self):
        validate_unit_for_type(self.goal_type, self.unit)
        return self


class DailyGoalUpdate(SQLModel):
    goal_type: Optional[DailyGoalType] = None
    name: Optional[str] = None
    target_value: Optional[float] = None
    unit: Optional[DailyGoalUnit] = None
    active: Optional[bool] = None
    milestone_id: Optional[uuid.UUID] = None
    days_of_week: Optional[List[int]] = None
    attributes: Optional[dict] = None

    _norm_days = field_validator("days_of_week")(lambda cls, v: normalize_days_of_week(v))

    @model_validator(mode="after")
    def _check_unit(self):
        # Only checkable when both are supplied; the service re-checks against the
        # stored goal_type for partial updates.
        if self.goal_type is not None:
            validate_unit_for_type(self.goal_type, self.unit)
        return self


class DailyGoalRead(SQLModel):
    id: uuid.UUID
    created_for: uuid.UUID
    milestone_id: Optional[uuid.UUID] = None
    goal_type: DailyGoalType
    name: str
    target_value: Optional[float] = None
    unit: Optional[DailyGoalUnit] = None
    active: bool
    days_of_week: Optional[List[int]] = None
    attributes: dict = {}
    created_at: datetime
    updated_at: datetime


class DailyGoalCompletion(SQLModel):
    daily_goal_id: uuid.UUID
    completed: bool = False
    value: Optional[float] = None
