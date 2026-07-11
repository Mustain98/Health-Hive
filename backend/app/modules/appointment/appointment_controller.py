from __future__ import annotations

from sqlmodel import Session
import uuid

from app.modules.user.models import User
from app.modules.appointment.models import Appointment, SessionRoom
from app.modules.appointment.appointment_service import (
    get_room_for_appointment,
    search_my_appointments_with_participants,
    consultant_search_appointments_with_participants,
)


def room_for_appointment(session: Session, appointment_id: uuid.UUID) -> SessionRoom:
    return get_room_for_appointment(session, appointment_id)


def get_consultant_history_controller(session: Session, consultant_profile_id: uuid.UUID, current_user: User) -> list[Appointment]:
    from app.modules.appointment.appointment_service import list_consultant_history
    from app.modules.consultant.models import ConsultantProfile
    from fastapi import HTTPException

    # Resolve Profile ID -> User ID
    profile = session.get(ConsultantProfile, consultant_profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Consultant profile not found")

    return list_consultant_history(session, profile.user_id, current_user.id)


def get_user_history_controller(session: Session, user_id: uuid.UUID) -> list[Appointment]:
    from app.modules.appointment.appointment_service import list_user_history
    return list_user_history(session, user_id)


def user_cancel_appointment(session: Session, me: User, appointment_id: uuid.UUID) -> Appointment:
    from app.modules.appointment.user_side_appointment_service import cancel_appointment
    return cancel_appointment(session, user_id=me.id, appointment_id=appointment_id)


def search_appointments_controller(
    session: Session,
    me: User,
    date: str | None = None,
    consultant_name: str | None = None
):
    from datetime import date as date_type

    parsed_date = None
    if date:
        try:
            parsed_date = date_type.fromisoformat(date)
        except ValueError:
            pass

    return search_my_appointments_with_participants(
        session, me.id, date=parsed_date, consultant_name=consultant_name
    )


def get_appointment_details_controller(session: Session, me: User, appointment_id: uuid.UUID):
    from app.modules.appointment.appointment_service import get_appointment_details_with_extras
    from app.modules.user.models import UserRead, UserType

    is_consultant = me.user_type == UserType.consultant

    appt, goal, target, meal_setting, consultant = get_appointment_details_with_extras(
        session, me.id, appointment_id, is_consultant=is_consultant
    )

    return {
        "appointment": appt,
        "goal": goal,
        "nutrition_target": target,
        "meal_plan_setting": meal_setting,
        "consultant": UserRead.model_validate(consultant) if consultant else None
    }


def toggle_permission_controller(session: Session, me: User, appointment_id: uuid.UUID, grant: bool) -> Appointment:
    from app.modules.appointment.appointment_service import toggle_appointment_permission
    return toggle_appointment_permission(session, me.id, appointment_id, grant)


def consultant_search_appointments_controller(
    session: Session,
    consultant: User,
    date: str | None = None,
    patient_name: str | None = None
):
    from datetime import date as date_type

    parsed_date = None
    if date:
        try:
            parsed_date = date_type.fromisoformat(date)
        except ValueError:
            pass

    return consultant_search_appointments_with_participants(
        session, consultant.id, date=parsed_date, patient_name=patient_name
    )
