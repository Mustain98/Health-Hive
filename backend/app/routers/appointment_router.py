from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.database import get_session
from app.core.auth import get_current_user, require_user_type
from app.models.user import User, UserType
from app.schemas.appointments import (
    AppointmentApplicationCreate,
    AppointmentApplicationRead,
    AppointmentSchedule,
    AppointmentRead,
    SessionRoomRead,
)
from app.controller.appointment_controller import (
    apply_me,
    my_applications,
    consultant_applications,
    consultant_reject,
    consultant_accept_and_schedule,
    my_appointments,
    consultant_appointments,
    room_for_appointment,
)

router = APIRouter(prefix="/appointments", tags=["Appointments"])


@router.post("/applications", response_model=AppointmentApplicationRead)
def apply_for_consultation(
    payload: AppointmentApplicationCreate,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    return apply_me(session, me, payload)


@router.get("/applications/me", response_model=list[AppointmentApplicationRead])
def list_my_apps(
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    return my_applications(session, me)


@router.get("/applications/consultant/me", response_model=list[AppointmentApplicationRead])
def list_consultant_apps(
    session: Session = Depends(get_session),
    consultant: User = Depends(require_user_type(UserType.consultant)),
):
    return consultant_applications(session, consultant)


@router.post("/applications/{application_id}/reject", response_model=AppointmentApplicationRead)
def reject_app(
    application_id: int,
    session: Session = Depends(get_session),
    consultant: User = Depends(require_user_type(UserType.consultant)),
):
    return consultant_reject(session, consultant, application_id)


@router.post("/applications/{application_id}/accept", response_model=AppointmentRead)
def accept_and_schedule_app(
    application_id: int,
    schedule: AppointmentSchedule,
    session: Session = Depends(get_session),
    consultant: User = Depends(require_user_type(UserType.consultant)),
):
    _, appt, _ = consultant_accept_and_schedule(session, consultant, application_id, schedule)
    return appt


@router.get("/me", response_model=list[AppointmentRead])
def list_my_appts(
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    return my_appointments(session, me)


@router.get("/consultant/me", response_model=list[AppointmentRead])
def list_consultant_appts(
    session: Session = Depends(get_session),
    consultant: User = Depends(require_user_type(UserType.consultant)),
):
    return consultant_appointments(session, consultant)


@router.get("/{appointment_id}/room", response_model=SessionRoomRead)
def get_room(
    appointment_id: int,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    # participant check happens in session endpoints; here we just return
    return room_for_appointment(session, appointment_id)
