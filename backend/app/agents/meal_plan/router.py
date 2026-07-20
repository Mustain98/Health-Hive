"""
meal_plan_router.py — REST endpoints for AI meal plan generation.
"""
import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.core.auth import get_current_user
from app.core.database import get_session
from app.modules.user.models import User
from app.agents.meal_plan import service as meal_plan_service

router = APIRouter(prefix="/meal-plans", tags=["Meal Plans"])


def _parse_overwrite_ids(body: dict | None) -> set[uuid.UUID] | None:
    """Read the optional per-slot overwrite allowlist from a generate body.
    Returns None (no resolution supplied → detect overlap) or a set of ids
    (resolution supplied, possibly empty = keep everything)."""
    raw = (body or {}).get("overwrite_timed_meal_ids")
    if raw is None:
        return None
    try:
        return {uuid.UUID(str(x)) for x in raw}
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="overwrite_timed_meal_ids must be a list of uuids")


_DOW_HELP = "weekdays are integers 0-6 (Mon=0 … Sun=6)"


def _coerce_day(value) -> int:
    try:
        day = int(value)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail=f"invalid weekday {value!r} — {_DOW_HELP}")
    if not 0 <= day <= 6:
        raise HTTPException(status_code=400, detail=f"weekday {day} out of range — {_DOW_HELP}")
    return day


def _parse_day_of_week(body: dict | None) -> int:
    """The weekday to generate; defaults to today's."""
    raw = (body or {}).get("day_of_week")
    return date.today().weekday() if raw is None else _coerce_day(raw)


def _parse_days(body: dict | None) -> list[int] | None:
    """The weekdays to generate; None means the whole Mon-Sun week."""
    raw = (body or {}).get("days")
    if raw is None:
        return None
    if not isinstance(raw, list) or not raw:
        raise HTTPException(status_code=400, detail=f"days must be a non-empty list — {_DOW_HELP}")
    return sorted({_coerce_day(d) for d in raw})


# ── Suggest setup (LLM: macro target + meal structure) ───────────────────────
@router.post("/suggest-setup")
def suggest_setup(
    body: dict | None = None,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """Suggest a nutrition target + meal structure. Body: { "apply": bool }.
    If apply=true, the suggested target is persisted as active."""
    apply = bool((body or {}).get("apply", False))
    try:
        return meal_plan_service.suggest_setup(session, me.id, apply=apply)
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Failed to suggest setup: {str(e)}")


# ── Resolve setup for the generation gate (consult-or-AI) ────────────────────
@router.post("/resolve-setup")
def resolve_setup(
    body: dict,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """When generation returns needs_setup. Body: { "choice": "ai_generate"|"consultation",
    "approve"?: bool }. ai_generate creates inactive drafts; approve=true activates + generates."""
    choice = (body or {}).get("choice")
    approve = bool((body or {}).get("approve", False))
    try:
        return meal_plan_service.resolve_setup(session, me.id, choice, approve)
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Failed to resolve setup: {str(e)}")


# ── Generate Day Plan ────────────────────────────────────────────────────────
@router.post("/generate-day")
def generate_day(
    body: dict,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """Generate a full day plan. Body: { "day_of_week"?: 0-6 } (Mon=0 … Sun=6; default today).
    Returns 409 { needs_setup, missing, options } if no active target/setting,
    or 409 { overlap, day_of_week, conflicts } if that weekday is already planned."""
    try:
        day_of_week = _parse_day_of_week(body)
        overwrite_ids = _parse_overwrite_ids(body)
        return meal_plan_service.generate_day_plan(session, me.id, day_of_week, overwrite_ids=overwrite_ids)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Failed to generate day plan: {str(e)}")


# ── Generate Week Plan ───────────────────────────────────────────────────────
@router.post("/generate-week")
def generate_week(
    body: dict,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """Generate the week's meal plan. Body: { "days"?: [0-6] } (Mon=0 … Sun=6; default all seven).
    Returns 409 { needs_setup, missing, options } if no active target/setting, or
    409 { overlap, days, conflicts } for the requested days that are already planned."""
    try:
        days = _parse_days(body)
        overwrite_ids = _parse_overwrite_ids(body)
        return meal_plan_service.generate_week_plan(session, me.id, days, overwrite_ids=overwrite_ids)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Failed to generate week plan: {str(e)}")


# ── Regenerate a single timed meal ───────────────────────────────────────────
@router.post("/timed-meal/{timed_meal_id}/regenerate")
def regenerate_timed_meal(
    timed_meal_id: uuid.UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    try:
        return meal_plan_service.regenerate_timed_meal(session, me.id, timed_meal_id)
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Failed to regenerate: {str(e)}")


# ── Regenerate a whole day ───────────────────────────────────────────────────
@router.post("/day/{day_plan_id}/regenerate")
def regenerate_day(
    day_plan_id: uuid.UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    try:
        return meal_plan_service.regenerate_day_plan(session, me.id, day_plan_id)
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Failed to regenerate day: {str(e)}")


# ── Deletes ──────────────────────────────────────────────────────────────────
@router.delete("/timed-meal/{timed_meal_id}")
def delete_timed_meal(
    timed_meal_id: uuid.UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    try:
        return meal_plan_service.delete_timed_meal(session, me.id, timed_meal_id)
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Failed to delete timed meal: {str(e)}")


@router.delete("/day/{day_plan_id}")
def delete_day(
    day_plan_id: uuid.UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    try:
        return meal_plan_service.delete_day_plan(session, me.id, day_plan_id)
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Failed to delete day plan: {str(e)}")


@router.delete("/week/{week_plan_id}")
def delete_week(
    week_plan_id: uuid.UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    try:
        return meal_plan_service.delete_week_plan(session, me.id, week_plan_id)
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Failed to delete week plan: {str(e)}")


# ── Swap Chosen Combo ────────────────────────────────────────────────────────
@router.patch("/timed-meal/{timed_meal_id}/swap")
def swap_combo(
    timed_meal_id: uuid.UUID,
    body: dict,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """Swap the chosen combo for a timed meal. Body: { "combo_option_id": "uuid" }."""
    option_id_str = (body or {}).get("combo_option_id")
    if not option_id_str:
        raise HTTPException(status_code=400, detail="combo_option_id required")
    try:
        combo_option_id = uuid.UUID(option_id_str)
        return meal_plan_service.swap_chosen_combo(session, me.id, timed_meal_id, combo_option_id)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Failed to swap: {str(e)}")


# ── Get My Plans ─────────────────────────────────────────────────────────────
@router.get("/me")
def get_my_plans(
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    try:
        return meal_plan_service.get_user_plans(session, me.id)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Failed to fetch plans: {str(e)}")
