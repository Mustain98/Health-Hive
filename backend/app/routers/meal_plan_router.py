"""
meal_plan_router.py — REST endpoints for AI-powered meal plan generation.
"""
import uuid
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.core.auth import get_current_user
from app.core.database import get_session
from app.models.user import User
from app.service import meal_plan_service

router = APIRouter(prefix="/meal-plans", tags=["Meal Plans"])


# ── Generate Day Plan ────────────────────────────────────────────────────────
@router.post("/generate-day")
def generate_day(
    body: dict,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """
    Generate a full day plan.
    Body: { "plan_date": "2025-03-10" }  (defaults to today if omitted)
    """
    try:
        plan_date_str = body.get("plan_date")
        if plan_date_str:
            plan_date = date.fromisoformat(plan_date_str)
        else:
            plan_date = date.today()

        result = meal_plan_service.generate_day_plan(session, me.id, plan_date)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate day plan: {str(e)}")


# ── Generate Week Plan ───────────────────────────────────────────────────────
@router.post("/generate-week")
def generate_week(
    body: dict,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """
    Generate a full 7-day week plan.
    Body: { "start_date": "2025-03-10" }  (defaults to today if omitted)
    """
    try:
        start_str = body.get("start_date")
        if start_str:
            start_date = date.fromisoformat(start_str)
        else:
            start_date = date.today()

        result = meal_plan_service.generate_week_plan(session, me.id, start_date)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate week plan: {str(e)}")


# ── Generate / Regenerate Single Timed Meal ──────────────────────────────────
@router.post("/timed-meal/{timed_meal_id}/regenerate")
def regenerate_timed_meal(
    timed_meal_id: uuid.UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """Regenerate 5 new combo options for a specific timed meal."""
    try:
        result = meal_plan_service.regenerate_timed_meal(session, me.id, timed_meal_id)
        session.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to regenerate: {str(e)}")


# ── Swap Chosen Combo ────────────────────────────────────────────────────────
@router.patch("/timed-meal/{timed_meal_id}/swap")
def swap_combo(
    timed_meal_id: uuid.UUID,
    body: dict,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """
    Swap the chosen combo for a timed meal.
    Body: { "combo_option_id": "uuid" }
    """
    option_id_str = body.get("combo_option_id")
    if not option_id_str:
        raise HTTPException(status_code=400, detail="combo_option_id required")

    try:
        combo_option_id = uuid.UUID(option_id_str)
        result = meal_plan_service.swap_chosen_combo(session, me.id, timed_meal_id, combo_option_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to swap: {str(e)}")


# ── Get My Plans ─────────────────────────────────────────────────────────────
@router.get("/me")
def get_my_plans(
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """Get all meal plans for the current user."""
    try:
        return meal_plan_service.get_user_plans(session, me.id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch plans: {str(e)}")


# ── Delete Day Plan ───────────────────────────────────────────────────────────
@router.delete("/day-plan/{day_plan_id}")
def delete_day_plan(
    day_plan_id: uuid.UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """Delete a specific day plan and all its timed meals."""
    try:
        meal_plan_service.delete_day_plan(session, me.id, day_plan_id)
        return {"detail": "Day plan deleted successfully."}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete day plan: {str(e)}")


# ── Regenerate Day Plan ───────────────────────────────────────────────────────
@router.post("/day-plan/{day_plan_id}/regenerate")
def regenerate_day_plan(
    day_plan_id: uuid.UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """Delete and re-generate a specific day plan."""
    try:
        result = meal_plan_service.regenerate_day_plan(session, me.id, day_plan_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to regenerate day plan: {str(e)}")


# ── Delete Week Plan ──────────────────────────────────────────────────────────
@router.delete("/week-plan/{week_plan_id}")
def delete_week_plan(
    week_plan_id: uuid.UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """Delete a full week plan and all its day plans."""
    try:
        meal_plan_service.delete_week_plan(session, me.id, week_plan_id)
        return {"detail": "Week plan deleted successfully."}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete week plan: {str(e)}")


# ── Regenerate Week Plan ──────────────────────────────────────────────────────
@router.post("/week-plan/{week_plan_id}/regenerate")
def regenerate_week_plan(
    week_plan_id: uuid.UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """Delete and re-generate a full week plan."""
    try:
        result = meal_plan_service.regenerate_week_plan(session, me.id, week_plan_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to regenerate week plan: {str(e)}")

