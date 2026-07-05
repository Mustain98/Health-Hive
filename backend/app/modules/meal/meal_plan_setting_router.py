from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, delete
from datetime import datetime

from app.core.database import get_session
from app.core.auth import get_current_user
from app.modules.user.models import User
from app.modules.meal.models import MealPlanSetting, MealPlanSettingTimedMeal
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
    session.flush()  # deactivate before inserting the new active row (partial unique index)

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
        meal_time = tm_data.get("meal_time")
        # Default to [meal_time] if no labels provided and the meal_time maps to a valid label
        from app.modules.meal.models import MealLabelName
        valid_label_values = {lbl.value for lbl in MealLabelName}
        default_labels = [meal_time] if meal_time in valid_label_values else []
        meal_labels = tm_data.get("meal_labels", default_labels)
        
        tm = MealPlanSettingTimedMeal(
            meal_plan_setting_id=new_setting.id,
            name=tm_data.get("name"),
            meal_time=meal_time,
            calories_pct=tm_data.get("calories_pct", 0),
            protein_g_pct=tm_data.get("protein_g_pct", 0),
            carbs_g_pct=tm_data.get("carbs_g_pct", 0),
            fat_g_pct=tm_data.get("fat_g_pct", 0),
            description=tm_data.get("description"),
            meal_labels=meal_labels,
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
    session.flush()  # deactivate before activating target (partial unique index)

    setting.active = True
    session.add(setting)
    session.commit()
    return {"message": "Setting activated"}


def _replace_timed_meals(session: Session, setting_id: uuid.UUID, timed_meals: list):
    """Drop and recreate a setting's timed meals from a payload list."""
    from app.modules.meal.models import MealLabelName
    valid_label_values = {lbl.value for lbl in MealLabelName}
    session.exec(delete(MealPlanSettingTimedMeal).where(
        MealPlanSettingTimedMeal.meal_plan_setting_id == setting_id))
    for tm_data in timed_meals:
        meal_time = tm_data.get("meal_time")
        default_labels = [meal_time] if meal_time in valid_label_values else []
        session.add(MealPlanSettingTimedMeal(
            meal_plan_setting_id=setting_id,
            name=tm_data.get("name"),
            meal_time=meal_time,
            calories_pct=tm_data.get("calories_pct", 0),
            protein_g_pct=tm_data.get("protein_g_pct", 0),
            carbs_g_pct=tm_data.get("carbs_g_pct", 0),
            fat_g_pct=tm_data.get("fat_g_pct", 0),
            description=tm_data.get("description"),
            meal_labels=tm_data.get("meal_labels", default_labels),
        ))


@router.put("/{setting_id}")
def update_setting(
    setting_id: uuid.UUID,
    payload: dict,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """Update a setting's name + timed meals (replaces the timed meals)."""
    setting = session.get(MealPlanSetting, setting_id)
    if not setting or setting.created_for != me.id:
        raise HTTPException(status_code=404, detail="Setting not found")
    if "name" in payload:
        setting.name = payload.get("name") or setting.name
    timed_meals = payload.get("timed_meals")
    if timed_meals is not None:
        setting.timed_meals_per_day = len(timed_meals)
        _replace_timed_meals(session, setting_id, timed_meals)
    setting.updated_at = utc_now()
    session.add(setting)
    session.commit()
    return {"message": "Setting updated", "id": str(setting.id)}


@router.delete("/{setting_id}")
def delete_setting(
    setting_id: uuid.UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """Delete a setting and its timed meals."""
    setting = session.get(MealPlanSetting, setting_id)
    if not setting or setting.created_for != me.id:
        raise HTTPException(status_code=404, detail="Setting not found")
    session.exec(delete(MealPlanSettingTimedMeal).where(
        MealPlanSettingTimedMeal.meal_plan_setting_id == setting_id))
    session.delete(setting)
    session.commit()
    return {"ok": True}

