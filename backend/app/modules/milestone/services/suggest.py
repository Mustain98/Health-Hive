"""Deterministic milestone proposals.

The AI describes these numbers; it does not invent them. Everything here is arithmetic
over the same constants `risk.py` enforces, so a proposal is safe **by construction** —
`is_risky_milestone` on the result is a tautology, not a hope. That is the whole point:
the old flow had the model guess a target, get it rejected by the guard, and then tell
the user to see a professional, because nothing in the loop could compute a number that
would pass.

No LLM call, no DB session — pure functions over body metrics, so the tool layer, the
finalize path and tests can all use them.
"""
from __future__ import annotations

from math import ceil
from typing import Optional

from app.modules.milestone.schemas import MilestoneType
from app.modules.milestone.services import risk
from app.utils.calculate import calculate_bmi

# Where we aim inside the healthy band. Not the edges: a target sitting exactly on
# BMI 18.5 is one bad week from being "unsafe" again, and the guard would flag any
# later downward revision. A little margin keeps the milestone stable.
TARGET_BMI_FROM_UNDERWEIGHT = 19.0
TARGET_BMI_FROM_OVERWEIGHT = 24.0

# Deliberately under MAX_WEEKLY_GAIN_KG (0.5) — proposing exactly at the ceiling means
# any rounding of duration tips the milestone over it.
GAIN_RATE_KG_PER_WEEK = 0.4

# Fraction of the loss ceiling we propose at, for the same reason.
LOSS_RATE_SAFETY_FACTOR = 0.8

# A single milestone never asks for more than this share of bodyweight — beyond it the
# timeframe stops being motivating, however safe the weekly rate is.
MAX_LOSS_FRACTION_PER_MILESTONE = 0.10

# Of lean weight gained on a sensible surplus, roughly half is muscle. Used to describe
# the muscle share of a gain honestly rather than promising all of it as muscle.
MUSCLE_SHARE_OF_GAIN = 0.55


def _duration_days(delta_kg: float, weekly_rate: float) -> int:
    """Whole weeks, always at least one."""
    return max(1, ceil(abs(delta_kg) / weekly_rate)) * 7


def propose_milestone(height_cm: Optional[float], weight_kg: Optional[float],
                      wants_muscle: bool = False) -> Optional[dict]:
    """A concrete, safe milestone for this body, or None if metrics are missing.

    `wants_muscle` only changes how the SAME weight trajectory is framed and typed —
    it never inflates the target, because muscle gain is bound by the same 0.5 kg/week
    ceiling as weight gain.
    """
    if not height_cm or not weight_kg:
        return None

    bmi = calculate_bmi(weight_kg, height_cm)
    status = risk.bmi_status(bmi)
    height_m = height_cm / 100.0

    if status == "underweight":
        target = round(TARGET_BMI_FROM_UNDERWEIGHT * height_m ** 2, 1)
        delta = target - weight_kg
        days = _duration_days(delta, GAIN_RATE_KG_PER_WEEK)
        muscle = round(delta * MUSCLE_SHARE_OF_GAIN, 1)
        return {
            "milestone_type": (MilestoneType.gain_muscle.value if wants_muscle
                               else MilestoneType.gain_weight.value),
            "name": "Healthy weight gain" + (" and muscle" if wants_muscle else ""),
            "target_weight": target,
            "duration_days": days,
            "weekly_rate_kg": GAIN_RATE_KG_PER_WEEK,
            "target_muscle_kg": muscle if wants_muscle else None,
            "rationale": (
                f"BMI {bmi} is below the healthy range, so this gains {round(delta, 1)} kg "
                f"to {target} kg (BMI {TARGET_BMI_FROM_UNDERWEIGHT}) over "
                f"{days // 7} weeks at {GAIN_RATE_KG_PER_WEEK} kg/week"
                + (f"; on a steady surplus with strength work roughly {muscle} kg of that "
                   f"is muscle" if wants_muscle else "")
            ),
        }

    if status == "overweight":
        healthy = round(TARGET_BMI_FROM_OVERWEIGHT * height_m ** 2, 1)
        floor = round(weight_kg * (1 - MAX_LOSS_FRACTION_PER_MILESTONE), 1)
        target = max(healthy, floor)  # never more than 10% of bodyweight in one milestone
        delta = weight_kg - target
        rate = round(risk.MAX_WEEKLY_LOSS_FRACTION * weight_kg * LOSS_RATE_SAFETY_FACTOR, 2)
        days = _duration_days(delta, rate)
        staged = target > healthy
        return {
            "milestone_type": MilestoneType.lose_weight.value,
            "name": "Steady weight loss",
            "target_weight": target,
            "duration_days": days,
            "weekly_rate_kg": rate,
            "target_muscle_kg": None,
            "rationale": (
                f"BMI {bmi} is above the healthy range, so this loses {round(delta, 1)} kg "
                f"to {target} kg over {days // 7} weeks at {rate} kg/week"
                + (" — a first stage, since one milestone stays within 10% of bodyweight"
                   if staged else f" (BMI {TARGET_BMI_FROM_OVERWEIGHT})")
            ),
        }

    # Healthy BMI. Weight is already where it should be, so the honest proposal is
    # recomposition (or maintenance) rather than moving the number for its own sake.
    if wants_muscle:
        muscle = 2.0
        days = _duration_days(muscle, GAIN_RATE_KG_PER_WEEK)
        return {
            "milestone_type": MilestoneType.recomposition.value,
            "name": "Build muscle, hold weight",
            "target_weight": weight_kg,
            "duration_days": days,
            "weekly_rate_kg": 0.0,
            "target_muscle_kg": muscle,
            "rationale": (
                f"BMI {bmi} is already healthy, so this holds weight at {weight_kg} kg and "
                f"adds about {muscle} kg of muscle over {days // 7} weeks"
            ),
        }
    return {
        "milestone_type": MilestoneType.maintain.value,
        "name": "Maintain healthy weight",
        "target_weight": weight_kg,
        "duration_days": 84,
        "weekly_rate_kg": 0.0,
        "target_muscle_kg": None,
        "rationale": f"BMI {bmi} is in the healthy range — this holds it there over 12 weeks",
    }
