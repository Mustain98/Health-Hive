from __future__ import annotations

from datetime import datetime
from sqlmodel import Session
import uuid

from app.models.user import User
from app.models.appointments import AppointmentApplication, Appointment, SessionRoom
from app.models.appointments import AppointmentApplicationCreate, AppointmentSchedule
from app.service.appointment_service import (
    list_my_applications,
    list_consultant_applications,
    reject_application,
    propose_time,
    accept_and_schedule,
    list_my_appointments,
    list_consultant_appointments,
    list_consultant_appointments_with_details,
    get_room_for_appointment,
    search_my_appointments_with_participants,
    consultant_search_appointments_with_participants,
)


def apply_me(session: Session, me: User, payload: AppointmentApplicationCreate) -> AppointmentApplication:
    from app.service.user_side_appointment_service import apply_for_appointment
    return apply_for_appointment(
        session,
        user_id=me.id,
        consultant_user_id=payload.consultant_user_id,
        requested_start_at=payload.requested_start_at,
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


def consultant_appointments(session: Session, consultant: User):
    from app.models.appointments import AppointmentReadWithUser
    from app.models.user import UserRead
    from app.models.user_data import UserData as UserDataRead

    items = list_consultant_appointments_with_details(session, consultant.id)
    
    results = []
    for appt, user, user_data, room in items:
        # Map to schema
        results.append(
            AppointmentReadWithUser(
                **appt.model_dump(),
                user=UserRead.model_validate(user),
                user_data=UserDataRead.model_validate(user_data) if user_data else None,
                session_status=room.status if room else None,
            )
        )
    return results




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


def consultant_propose_time(
    session: Session, consultant: User, application_id: int, proposed_start_at: datetime
) -> AppointmentApplication:
    return propose_time(
        session,
        consultant_user_id=consultant.id,
        application_id=application_id,
        proposed_start_at=proposed_start_at,
    )


def user_accept_proposal_controller(session: Session, me: User, application_id: int) -> AppointmentApplication:
    from app.service.user_side_appointment_service import user_accept_proposal
    return user_accept_proposal(session, user_id=me.id, application_id=application_id)


def user_cancel_application(session: Session, me: User, application_id: int) -> AppointmentApplication:
    from app.service.user_side_appointment_service import cancel_application
    return cancel_application(session, user_id=me.id, application_id=application_id)


def user_cancel_appointment(session: Session, me: User, appointment_id: int) -> Appointment:
    from app.service.user_side_appointment_service import cancel_appointment
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


def get_appointment_details_controller(session: Session, me: User, appointment_id: int):
    from app.service.appointment_service import get_appointment_details_with_extras
    from app.models.user import UserRead, UserType

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
    from app.service.appointment_service import toggle_appointment_permission
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
