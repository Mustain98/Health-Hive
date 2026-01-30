from __future__ import annotations

from datetime import datetime
from sqlmodel import Session

from app.models.user import User
from app.models.appointments import AppointmentApplication, Appointment, SessionRoom
from app.schemas.appointments import AppointmentApplicationCreate, AppointmentSchedule
from app.service.appointment_service import (
    apply_for_appointment,
    list_my_applications,
    list_consultant_applications,
    reject_application,
    accept_and_schedule,
    list_my_appointments,
    list_consultant_appointments,
    get_room_for_appointment,
)


def apply_me(session: Session, me: User, payload: AppointmentApplicationCreate) -> AppointmentApplication:
    return apply_for_appointment(
        session,
        user_id=me.id,
        consultant_user_id=payload.consultant_user_id,
        note_from_user=payload.note_from_user,
    )


def my_applications(session: Session, me: User) -> list[AppointmentApplication]:
    return list_my_applications(session, me.id)


def consultant_applications(session: Session, consultant: User) -> list[AppointmentApplication]:
    return list_consultant_applications(session, consultant.id)


def consultant_reject(session: Session, consultant: User, application_id: int) -> AppointmentApplication:
    return reject_application(session, consultant.id, application_id)


def consultant_accept_and_schedule(
    session: Session,
    consultant: User,
    application_id: int,
    schedule: AppointmentSchedule,
) -> tuple[AppointmentApplication, Appointment, SessionRoom]:
    return accept_and_schedule(
        session,
        consultant.id,
        application_id,
        schedule.scheduled_start_at,
        schedule.scheduled_end_at,
    )


def my_appointments(session: Session, me: User) -> list[Appointment]:
    return list_my_appointments(session, me.id)


def consultant_appointments(session: Session, consultant: User) -> list[Appointment]:
    return list_consultant_appointments(session, consultant.id)



def room_for_appointment(session: Session, appointment_id: int) -> SessionRoom:
    return get_room_for_appointment(session, appointment_id)


def get_consultant_history_controller(session: Session, consultant_profile_id: int, current_user: User) -> list[Appointment]:
    from app.service.appointment_service import list_consultant_history
    from app.models.consultant import ConsultantProfile
    from sqlmodel import select
    from fastapi import HTTPException

    # Resolve Profile ID -> User ID
    profile = session.get(ConsultantProfile, consultant_profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Consultant profile not found")
    
    return list_consultant_history(session, profile.user_id, current_user.id)


def get_user_history_controller(session: Session, user_id: int) -> list[Appointment]:
    from app.service.appointment_service import list_user_history
    return list_user_history(session, user_id)
