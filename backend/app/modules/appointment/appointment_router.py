from uuid import UUID

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.database import get_session
from app.core.auth import get_current_user, require_user_type
from app.modules.user.models import User, UserType
from app.modules.appointment.models import (
    Appointment,
    AppointmentWithParticipants,
    SessionRoom,
    AppointmentDetailsResponse,
)
from app.modules.appointment.appointment_controller import (
    room_for_appointment,
    user_cancel_appointment,
)

router = APIRouter(prefix="/appointments", tags=["Appointments"])


@router.get("/me", response_model=list[AppointmentWithParticipants])
def list_my_appts(
    date: str | None = None,
    consultant_name: str | None = None,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    from app.modules.appointment.appointment_controller import search_appointments_controller
    return search_appointments_controller(session, me, date, consultant_name)


@router.get("/{appointment_id}/details", response_model=AppointmentDetailsResponse)
def get_appointment_details(
    appointment_id: UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    from app.modules.appointment.appointment_controller import get_appointment_details_controller
    # Returns AppointmentDetailsResponse dict structure
    return get_appointment_details_controller(session, me, appointment_id)


@router.put("/{appointment_id}/permission", response_model=Appointment)
def toggle_permission(
    appointment_id: UUID,
    grant: bool,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    from app.modules.appointment.appointment_controller import toggle_permission_controller
    return toggle_permission_controller(session, me, appointment_id, grant)


@router.get("/consultant/me", response_model=list[AppointmentWithParticipants])
def list_consultant_appts(
    date: str | None = None,
    patient_name: str | None = None,
    session: Session = Depends(get_session),
    consultant: User = Depends(require_user_type(UserType.consultant)),
):
    from app.modules.appointment.appointment_controller import consultant_search_appointments_controller
    return consultant_search_appointments_controller(session, consultant, date, patient_name)


@router.get("/{appointment_id}/room", response_model=SessionRoom)
def get_room(
    appointment_id: UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    # participant check happens in session endpoints; here we just return
    return room_for_appointment(session, appointment_id)


# ---------- User-side endpoints ----------

@router.post("/appointments/{appointment_id}/cancel", response_model=Appointment)
def cancel_appointment_endpoint(
    appointment_id: UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    return user_cancel_appointment(session, me, appointment_id)


# ---------- History endpoints ----------

@router.get("/consultants/{consultant_id}/history", response_model=list[Appointment])
def get_consultant_history(
    consultant_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    from app.modules.appointment.appointment_controller import get_consultant_history_controller
    history = get_consultant_history_controller(session, consultant_id, current_user)
    return history


@router.get("/users/{user_id}/history", response_model=list[Appointment])
def get_user_history(
    user_id: UUID,
    session: Session = Depends(get_session),
    consultant: User = Depends(require_user_type(UserType.consultant)),
):
    from app.modules.appointment.appointment_controller import get_user_history_controller
    return get_user_history_controller(session, user_id)
