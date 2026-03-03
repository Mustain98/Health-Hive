from __future__ import annotations

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models.user_goal import UserGoal
from app.models.nutrition_target import NutritionTarget, NutritionTargetUpdate
from app.models.appointments import Appointment
from app.service.user_goal_service import get_goal_for_user, create_goal_for_user
from app.service.nutrition_target_service import get_current_target, create_target_for_user
import uuid


# Permission check
def has_active_access(session: Session, user_id: uuid.UUID, consultant_user_id: uuid.UUID) -> bool:
    # Check if ANY completed/scheduled appointment exists where consultant_access is True
    exists = session.exec(
        select(Appointment)
        .where(Appointment.user_id == user_id)
        .where(Appointment.consultant_user_id == consultant_user_id)
        .where(Appointment.consultant_access == True)
    ).first()
    return bool(exists)


def consultant_read_goal(session: Session, consultant_user_id: uuid.UUID, user_id: uuid.UUID) -> UserGoal:
    if not has_active_access(session, user_id, consultant_user_id):
         raise HTTPException(status_code=403, detail="User has revoked access or no appointment found.")
    return get_goal_for_user(session, user_id)


def consultant_create_goal(
    session: Session, 
    consultant_user_id: uuid.UUID, 
    user_id: uuid.UUID, 
    payload: UserGoal, 
    appointment_id: uuid.UUID | None = None
) -> UserGoal:
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
