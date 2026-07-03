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
from app.modules.meal_planner_agent import meal_plan_service

router = APIRouter(prefix="/meal-plans", tags=["Meal Plans"])


def _macro_source(body: dict) -> str:
    ms = (body or {}).get("macro_source", "current")
    return ms if ms in ("current", "auto") else "current"


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


# ── Generate Day Plan ────────────────────────────────────────────────────────
@router.post("/generate-day")
def generate_day(
    body: dict,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """Generate a full day plan. Body: { "plan_date"?: "YYYY-MM-DD", "macro_source"?: "current"|"auto" }."""
    try:
        plan_date_str = (body or {}).get("plan_date")
        plan_date = date.fromisoformat(plan_date_str) if plan_date_str else date.today()
        return meal_plan_service.generate_day_plan(session, me.id, plan_date, macro_source=_macro_source(body))
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
    """Generate a full 7-day week plan. Body: { "start_date"?: "YYYY-MM-DD", "macro_source"?: "current"|"auto" }."""
    try:
        start_str = (body or {}).get("start_date")
        start_date = date.fromisoformat(start_str) if start_str else date.today()
        return meal_plan_service.generate_week_plan(session, me.id, start_date, macro_source=_macro_source(body))
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
