"""Milestone schemas — the long-term aim a Plan is built around.

`GoalType` lives here (not in `daily_goal/`) because it is derived from `MilestoneType`
via `goal_type_for_milestone`. It is the single sanctioned cross-part import: `daily_goal/`
imports it from here. A *second* cross-part import would mean that logic belongs in `plan/`.
"""
from datetime import datetime, date
from enum import Enum
from typing import Optional

from pydantic import ConfigDict
from sqlmodel import SQLModel, Field

from app.utils.time import utc_now


# ── Enums ──────────────────────────────────────────────────────────────────

class GoalType(str, Enum):
    lose = "lose"
    gain = "gain"
    maintain = "maintain"


class MilestoneUnit(str, Enum):
    """Closed unit vocabulary for a milestone target. Was free text."""
    kg = "kg"
    lb = "lb"
    pct_body_fat = "pct_body_fat"


class MilestoneType(str, Enum):
    """Long-term, non-destructive aim. Richer than GoalType; maps down to a
    GoalType for the macro pipeline (see milestone service).

    The column is plain VARCHAR (migration 0002), so adding members here needs no
    data migration."""
    lose_weight = "lose_weight"
    gain_weight = "gain_weight"
    gain_muscle = "gain_muscle"
    maintain = "maintain"
    # Mixed goal: lose fat AND gain muscle at the same time (body recomposition).
    recomposition = "recomposition"
    # Escape hatch so any dynamic milestone fits: the name + attributes describe it.
    custom = "custom"


# ── Milestone <-> GoalType mapping ─────────────────────────────────────────

_MILESTONE_TO_GOAL = {
    MilestoneType.lose_weight: GoalType.lose,
    MilestoneType.gain_weight: GoalType.gain,
    MilestoneType.gain_muscle: GoalType.gain,
    MilestoneType.maintain: GoalType.maintain,
    # Recomposition eats at ≈maintenance calories with high protein — the deficit/
    # surplus nuance lives in the nutrition target, not the macro direction.
    MilestoneType.recomposition: GoalType.maintain,
    # Safe default for anything free-form; the nutrition target refines it.
    MilestoneType.custom: GoalType.maintain,
}


def goal_type_for_milestone(milestone_type: Optional[MilestoneType]) -> Optional[GoalType]:
    """Map the richer milestone_type down to the GoalType the macro pipeline uses."""
    if milestone_type is None:
        return None
    return _MILESTONE_TO_GOAL.get(milestone_type)


# ── Dynamic `attributes` validation ────────────────────────────────────────

class _MilestoneAttrBase(SQLModel):
    model_config = ConfigDict(extra="forbid")


class WeightMilestoneAttrs(_MilestoneAttrBase):
    """lose_weight / gain_weight / maintain."""
    weekly_rate_kg: Optional[float] = Field(default=None, ge=0, le=2)
    note: Optional[str] = None


class MuscleMilestoneAttrs(_MilestoneAttrBase):
    """gain_muscle."""
    target_muscle_kg: Optional[float] = Field(default=None, ge=0, le=50)
    note: Optional[str] = None


class RecompositionAttrs(_MilestoneAttrBase):
    """recomposition — both directions at once, so both targets are expressible."""
    target_muscle_kg: Optional[float] = Field(default=None, ge=0, le=50)
    target_fat_loss_kg: Optional[float] = Field(default=None, ge=0, le=100)
    note: Optional[str] = None


class CustomMilestoneAttrs(_MilestoneAttrBase):
    """custom — the deliberate free-form pocket. `metrics` may carry any numbers the
    milestone needs (e.g. {"run_5k_min": 25}); everything else stays schema-checked."""
    note: Optional[str] = None
    metrics: Optional[dict] = None


_MILESTONE_ATTR_MODELS = {
    MilestoneType.lose_weight: WeightMilestoneAttrs,
    MilestoneType.gain_weight: WeightMilestoneAttrs,
    MilestoneType.maintain: WeightMilestoneAttrs,
    MilestoneType.gain_muscle: MuscleMilestoneAttrs,
    MilestoneType.recomposition: RecompositionAttrs,
    MilestoneType.custom: CustomMilestoneAttrs,
}


def validate_milestone_attributes(milestone_type: Optional[MilestoneType], attributes: Optional[dict]) -> dict:
    """Validate + normalize a milestone's JSON attributes. Raises ValueError.

    Previously accepted *any* dict, so the LLM could write arbitrary keys. All 22
    production rows have `attributes = {}`, so closing this breaks nothing.
    """
    if attributes is None:
        return {}
    if not isinstance(attributes, dict):
        raise ValueError("attributes must be a JSON object")
    if milestone_type is None:
        return {} if not attributes else dict(attributes)
    model = _MILESTONE_ATTR_MODELS.get(milestone_type, WeightMilestoneAttrs)
    return model.model_validate(attributes).model_dump(exclude_none=True)


# ── Schemas ────────────────────────────────────────────────────────────────

class MilestoneLogCreate(SQLModel):
    weight: float
    date: Optional[datetime] = None  # defaults to today in service


class MilestoneUpdate(SQLModel):
    active: bool = Field(default_factory=False, nullable=False)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    updated_at: Optional[datetime] = utc_now


class GoalDateChangeRequest(SQLModel):
    new_start_date: date

