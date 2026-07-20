from __future__ import annotations

from fastapi import HTTPException
from sqlmodel import Session, select

from datetime import date

from app.modules.milestone.models import Milestone
from app.modules.nutrition_target.models import NutritionTarget
from app.modules.nutrition_target.schemas import NutritionTargetUpdate
from app.modules.appointment.models import Appointment, FollowUpRoom, FollowUpRoomStatus
from app.modules.meal_plan_setting.models import MealPlanSetting, MealPlanSettingTimedMeal
from app.modules.milestone.services import get_goal_for_user, create_goal_for_user
from app.modules.daily_goal import services as dg_service
from app.modules.nutrition_target.services import get_current_target, create_target_for_user
from app.modules.plan import services as plan_service
import uuid


# Permission check: the consultant is connected via a session/appointment the user
# hasn't revoked (consultant_access) OR an active follow-up room (either party can cancel).
def has_active_access(session: Session, user_id: uuid.UUID, consultant_user_id: uuid.UUID) -> bool:
    exists = session.exec(
        select(Appointment)
        .where(Appointment.user_id == user_id)
        .where(Appointment.consultant_user_id == consultant_user_id)
        .where(Appointment.consultant_access == True)
    ).first()
    if exists:
        return True
    room = session.exec(
        select(FollowUpRoom)
        .where(FollowUpRoom.user_id == user_id)
        .where(FollowUpRoom.consultant_user_id == consultant_user_id)
        .where(FollowUpRoom.status == FollowUpRoomStatus.active)
    ).first()
    return bool(room)


def _require_access(session: Session, user_id: uuid.UUID, consultant_user_id: uuid.UUID) -> None:
    if not has_active_access(session, user_id, consultant_user_id):
        raise HTTPException(status_code=403, detail="User has revoked access or no appointment found.")


def consultant_read_goal(session: Session, consultant_user_id: uuid.UUID, user_id: uuid.UUID) -> Milestone:
    if not has_active_access(session, user_id, consultant_user_id):
         raise HTTPException(status_code=403, detail="User has revoked access or no appointment found.")
    return get_goal_for_user(session, user_id)


def consultant_create_goal(
    session: Session, 
    consultant_user_id: uuid.UUID, 
    user_id: uuid.UUID, 
    payload: Milestone, 
    appointment_id: uuid.UUID | None = None
) -> Milestone:
    # No permission check here as per user requirement: "consultants dont need permission fro user to create"
    
    # Force set created_by
    payload.created_by = consultant_user_id
    
    # Force active=False so user has to choose to activate it
    payload.active = False

    # Force appointment match check? 
    if appointment_id:
        appt = session.get(Appointment, appointment_id)
        if appt and (appt.user_id != user_id or appt.consultant_user_id != consultant_user_id):
            raise HTTPException(status_code=400, detail="Appointment mismatch")

    return create_goal_for_user(session, user_id, payload, appointment_id)


def consultant_read_target(session: Session, consultant_user_id: uuid.UUID, user_id: uuid.UUID) -> NutritionTarget:
    if not has_active_access(session, user_id, consultant_user_id):
         raise HTTPException(status_code=403, detail="User has revoked access or no appointment found.")
    
    t = get_current_target(session, user_id)
    if not t:
        # raise HTTPException(status_code=404, detail="Nutrition target not found")
        return None # Return None if not found, let router/controller handle or return null
    return t


def consultant_create_target(
    session: Session, 
    consultant_user_id: uuid.UUID, 
    user_id: uuid.UUID, 
    payload: NutritionTargetUpdate, 
    appointment_id: uuid.UUID | None = None
) -> NutritionTarget:
    # No permission check here
    
    # Force active=False
    payload.active = False

    if appointment_id:
        appt = session.get(Appointment, appointment_id)
        if appt and (appt.user_id != user_id or appt.consultant_user_id != consultant_user_id):
            raise HTTPException(status_code=400, detail="Appointment mismatch")

    return create_target_for_user(session, user_id, payload, created_by=consultant_user_id, appointment_id=appointment_id)

def consultant_read_meal_plan_setting(session: Session, consultant_user_id: uuid.UUID, user_id: uuid.UUID):
    if not has_active_access(session, user_id, consultant_user_id):
         raise HTTPException(status_code=403, detail="User has revoked access or no appointment found.")
    
    # Get the active one
    statement = select(MealPlanSetting).where(MealPlanSetting.created_for == user_id, MealPlanSetting.active == True)
    setting = session.exec(statement).first()
    if not setting:
        return None
        
    data = setting.model_dump()
    data["timed_meals"] = [tm.model_dump() for tm in setting.timed_meals]
    return data

def consultant_create_meal_plan_setting(
    session: Session, 
    consultant_user_id: uuid.UUID, 
    user_id: uuid.UUID, 
    payload: dict, 
    appointment_id: uuid.UUID | None = None
):
    if appointment_id:
        appt = session.get(Appointment, appointment_id)
        if appt and (appt.user_id != user_id or appt.consultant_user_id != consultant_user_id):
            raise HTTPException(status_code=400, detail="Appointment mismatch")

    new_setting = MealPlanSetting(
        name=payload.get("name", "Consultant Suggested Plan"),
        timed_meals_per_day=payload.get("timed_meals_per_day", 3),
        created_for=user_id,
        created_by=consultant_user_id,
        appointment_id=appointment_id,
        active=False  # User must adopt it
    )
    session.add(new_setting)
    session.commit()
    session.refresh(new_setting)
    
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
    
    # Return it eager loaded
    session.refresh(new_setting)
    data = new_setting.model_dump()
    data["timed_meals"] = [tm.model_dump() for tm in new_setting.timed_meals]
    return data


# ── Daily goals / logs / plans (read) + whole-plan build ───────────────────

def consultant_read_daily_goals(session: Session, consultant_user_id: uuid.UUID, user_id: uuid.UUID) -> list[dict]:
    _require_access(session, user_id, consultant_user_id)
    return [{
        "id": str(g.id), "name": g.name,
        "goal_type": g.goal_type.value if hasattr(g.goal_type, "value") else g.goal_type,
        "target_value": g.target_value, "unit": g.unit, "active": g.active,
        "days_of_week": g.days_of_week, "attributes": g.attributes,
        "plan_id": str(g.plan_id) if g.plan_id else None,
        "created_at": str(g.created_at),
    } for g in dg_service.list_daily_goals(session, user_id)]


def consultant_read_daily_goal_logs(session: Session, consultant_user_id: uuid.UUID, user_id: uuid.UUID,
                                    start: date | None = None, end: date | None = None) -> list[dict]:
    _require_access(session, user_id, consultant_user_id)
    return dg_service.get_log_history(session, user_id, start, end)


def consultant_read_plans(session: Session, consultant_user_id: uuid.UUID, user_id: uuid.UUID) -> list[dict]:
    _require_access(session, user_id, consultant_user_id)
    return plan_service.list_plans(session, user_id)


def consultant_build_plan(session: Session, consultant_user_id: uuid.UUID, user_id: uuid.UUID,
                          payload: dict) -> dict:
    _require_access(session, user_id, consultant_user_id)
    return plan_service.create_plan_for_client(session, consultant_user_id, user_id, payload)
