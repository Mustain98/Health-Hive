from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from datetime import datetime

from app.core.database import get_session
from app.core.auth import get_current_user
from app.models.user import User
from app.models.meal_plan.meal_plan_setting import MealPlanSetting, MealPlanSettingTimedMeal
from app.utils.time import utc_now

router = APIRouter(prefix="/meal-plan-settings", tags=["Meal Plan Settings"])

# -- User Endpoints --

@router.get("/me")
def get_my_settings(
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """Get all Meal Plan Settings (active, inactive, and suggested) for the current user."""
    statement = select(MealPlanSetting).where(MealPlanSetting.created_for == me.id).order_by(MealPlanSetting.created_at.desc())
    settings = session.exec(statement).all()
    
    # Eagerly load the timed meals and creator info
    result = []
    for s in settings:
        data = s.model_dump()
        data["timed_meals"] = [tm.model_dump() for tm in s.timed_meals]
        
        creator = session.get(User, s.created_by)
        if creator and creator.id != me.id:
            data["created_by_name"] = creator.full_name or creator.username
            data["created_by_email"] = creator.email
            
        result.append(data)
    return result

@router.post("/me")
def create_my_setting(
    payload: dict,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """User creates their own meal plan setting (automatically making it active)."""
    # Deactivate current
    active_statement = select(MealPlanSetting).where(MealPlanSetting.created_for == me.id, MealPlanSetting.active == True)
    for existing in session.exec(active_statement):
        existing.active = False
        session.add(existing)
        
    new_setting = MealPlanSetting(
        name=payload.get("name", "Custom Plan"),
        timed_meals_per_day=payload.get("timed_meals_per_day", 3),
        created_for=me.id,
        created_by=me.id,
        active=True
    )
    session.add(new_setting)
    session.commit()
    session.refresh(new_setting)
    
    # Create timed meals
    for tm_data in payload.get("timed_meals", []):
        tm = MealPlanSettingTimedMeal(
            meal_plan_setting_id=new_setting.id,
            name=tm_data.get("name"),
            meal_time=tm_data.get("meal_time"),
            calories_pct=tm_data.get("calories_pct", 0),
            protein_g_pct=tm_data.get("protein_g_pct", 0),
            carbs_g_pct=tm_data.get("carbs_g_pct", 0),
            fat_g_pct=tm_data.get("fat_g_pct", 0)
        )
        session.add(tm)
    
    session.commit()
    return {"message": "Created successfully", "id": new_setting.id}

@router.patch("/{setting_id}/activate")
def activate_setting(
    setting_id: uuid.UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user)
):
    """Adopt a suggested setting or re-activate a past one."""
    setting = session.get(MealPlanSetting, setting_id)
    if not setting or setting.created_for != me.id:
        raise HTTPException(status_code=404, detail="Setting not found")
        
    # Deactivate current
    active_statement = select(MealPlanSetting).where(MealPlanSetting.created_for == me.id, MealPlanSetting.active == True)
    for existing in session.exec(active_statement):
        existing.active = False
        session.add(existing)
        
    setting.active = True
    session.add(setting)
    session.commit()
    return {"message": "Setting activated"}

