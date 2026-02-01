from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models.appointments import (
    AppointmentApplication,
    ApplicationStatus,
    Appointment,
    AppointmentStatus,
    SessionRoom,
    SessionStatus,
)
from app.models.user import User, UserType
from app.models.user_data import UserData


def utc_now_naive() -> datetime:
    """Always store naive UTC in DB."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _ensure_consultant(session: Session, consultant_user_id: int) -> User:
    u = session.get(User, consultant_user_id)
    if not u:
        raise HTTPException(status_code=404, detail="Consultant not found")
    if u.user_type != UserType.consultant:
        raise HTTPException(status_code=400, detail="Target user is not a consultant")
    return u


def list_my_applications(session: Session, user_id: int) -> list[AppointmentApplication]:
    return list(
        session.exec(
            select(AppointmentApplication)
            .where(AppointmentApplication.user_id == user_id)
            .order_by(AppointmentApplication.created_at.desc())
        ).all()
    )


def list_consultant_applications(session: Session, consultant_user_id: int) -> list[AppointmentApplication]:
    return list(
        session.exec(
            select(AppointmentApplication)
            .where(AppointmentApplication.consultant_user_id == consultant_user_id)
            .order_by(AppointmentApplication.created_at.desc())
        ).all()
    )


def reject_application(session: Session, consultant_user_id: int, application_id: int) -> AppointmentApplication:
    _ensure_consultant(session, consultant_user_id)

    app = session.get(AppointmentApplication, application_id)
    if not app:
        raise HTTPException(404, "Application not found")
    if app.consultant_user_id != consultant_user_id:
        raise HTTPException(403, "Not your application")
    if app.status != ApplicationStatus.submitted:
        raise HTTPException(400, "Application is not in submitted state")

    now = utc_now_naive()
    app.status = ApplicationStatus.rejected
    app.updated_at = now

    session.add(app)
    session.commit()
    session.refresh(app)
    return app


def propose_time(
    session: Session,
    *,
    consultant_user_id: int,
    application_id: int,
    proposed_start_at: datetime,
) -> AppointmentApplication:
    _ensure_consultant(session, consultant_user_id)

    app = session.get(AppointmentApplication, application_id)
    if not app:
        raise HTTPException(404, "Application not found")
    if app.consultant_user_id != consultant_user_id:
        raise HTTPException(403, "Not your application")
    if app.status not in (ApplicationStatus.submitted, ApplicationStatus.proposed):
        raise HTTPException(400, "Cannot propose in this state")

    # normalize to naive UTC
    if proposed_start_at.tzinfo is not None:
        proposed_start_at = proposed_start_at.astimezone(timezone.utc).replace(tzinfo=None)

    now = utc_now_naive()
    if proposed_start_at < now:
        raise HTTPException(400, "Cannot propose a time in the past")

    app.proposed_start_at = proposed_start_at
    app.proposed_at = now
    app.status = ApplicationStatus.proposed
    app.updated_at = now

    session.add(app)
    session.commit()
    session.refresh(app)
    return app


def schedule_from_application(
    session: Session,
    *,
    consultant_user_id: int,
    application_id: int,
    scheduled_end_at: datetime,
) -> tuple[AppointmentApplication, Appointment, SessionRoom]:
    _ensure_consultant(session, consultant_user_id)

    app = session.get(AppointmentApplication, application_id)
    if not app:
        raise HTTPException(404, "Application not found")
    if app.consultant_user_id != consultant_user_id:
        raise HTTPException(403, "Not your application")

    if app.status not in (ApplicationStatus.submitted, ApplicationStatus.proposal_accepted):
        raise HTTPException(400, "Application is not ready to schedule")

    # prevent double scheduling
    existing = session.exec(select(Appointment).where(Appointment.application_id == app.id)).first()
    if existing:
        raise HTTPException(409, "Appointment already created for this application")

    # start depends on state
    if app.status == ApplicationStatus.proposal_accepted:
        if not app.proposed_start_at:
            raise HTTPException(400, "Proposed start time missing")
        scheduled_start_at = app.proposed_start_at
    else:
        scheduled_start_at = app.requested_start_at

    # normalize end to naive UTC
    if scheduled_end_at.tzinfo is not None:
        scheduled_end_at = scheduled_end_at.astimezone(timezone.utc).replace(tzinfo=None)

    now = utc_now_naive()

    if scheduled_end_at <= scheduled_start_at:
        raise HTTPException(400, "scheduled_end_at must be after start")
    if scheduled_end_at <= now:
        raise HTTPException(400, "scheduled_end_at must be in the future")

    # overlap check
    overlap = session.exec(
        select(Appointment)
        .where(Appointment.consultant_user_id == consultant_user_id)
        .where(Appointment.status == AppointmentStatus.scheduled)
        .where(Appointment.scheduled_start_at < scheduled_end_at)
        .where(Appointment.scheduled_end_at > scheduled_start_at)
    ).first()
    if overlap:
        raise HTTPException(409, "Time overlaps an existing appointment")

    appt = Appointment(
        application_id=app.id,
        user_id=app.user_id,
        consultant_user_id=consultant_user_id,
        scheduled_start_at=scheduled_start_at,
        scheduled_end_at=scheduled_end_at,
        status=AppointmentStatus.scheduled,
        created_at=now,
        updated_at=now,
    )
    session.add(appt)
    session.flush()  # ✅ assigns appt.id without committing

    existing_room = session.exec(select(SessionRoom).where(SessionRoom.appointment_id == appt.id)).first()
    if not existing_room:
        room = SessionRoom(
            appointment_id=appt.id,
            status=SessionStatus.not_started,
            created_at=now,
            updated_at=now,
        )
        session.add(room)
    else:
        room = existing_room

    app.status = ApplicationStatus.scheduled
    app.updated_at = now
    session.add(app)

    session.commit()
    session.refresh(app)
    session.refresh(appt)
    session.refresh(room)

    return app, appt, room


def list_my_appointments(session: Session, user_id: int) -> list[Appointment]:
    return list(
        session.exec(
            select(Appointment)
            .where(Appointment.user_id == user_id)
            .order_by(Appointment.scheduled_start_at.desc())
        ).all()
    )


def get_room_for_appointment(session: Session, appointment_id: int) -> SessionRoom:
    room = session.exec(select(SessionRoom).where(SessionRoom.appointment_id == appointment_id)).first()
    if not room:
        raise HTTPException(404, "Session room not found")
    return room


def accept_and_schedule(
    session: Session,
    consultant_user_id: int,
    application_id: int,
    scheduled_start_at: datetime,
    scheduled_end_at: datetime,
) -> tuple[AppointmentApplication, Appointment, SessionRoom]:
    """
    Wrapper for schedule_from_application that accepts both start and end times.
    If application is submitted, uses requested_start_at.
    If application is proposal_accepted, uses proposed_start_at.
    The scheduled_start_at parameter is ignored; only scheduled_end_at is used.
    """
    return schedule_from_application(
        session,
        consultant_user_id=consultant_user_id,
        application_id=application_id,
        scheduled_end_at=scheduled_end_at,
    )


def list_consultant_appointments(session: Session, consultant_user_id: int) -> list[Appointment]:
    """List all appointments for a consultant."""
    return list(
        session.exec(
            select(Appointment)
            .where(Appointment.consultant_user_id == consultant_user_id)
            .order_by(Appointment.scheduled_start_at.desc())
        ).all()
    )


def list_consultant_appointments_with_details(
    session: Session, consultant_user_id: int
) -> list[tuple[Appointment, User, Optional[UserData], Optional[SessionRoom]]]:
    from app.models.user_data import UserData

    return list(
        session.exec(
            select(Appointment, User, UserData, SessionRoom)
            .join(User, Appointment.user_id == User.id)
            .outerjoin(UserData, User.id == UserData.user_id)
            .outerjoin(SessionRoom, Appointment.id == SessionRoom.appointment_id)
            .where(Appointment.consultant_user_id == consultant_user_id)
            .order_by(Appointment.scheduled_start_at.desc())
        ).all()
    )



def list_consultant_history(session: Session, consultant_user_id: int, user_id: int) -> list[Appointment]:
    """List completed appointments between a consultant and a specific user."""
    return list(
        session.exec(
            select(Appointment)
            .where(Appointment.consultant_user_id == consultant_user_id)
            .where(Appointment.user_id == user_id)
            .where(Appointment.status == AppointmentStatus.completed)
            .order_by(Appointment.scheduled_start_at.desc())
        ).all()
    )


def list_user_history(session: Session, user_id: int) -> list[Appointment]:
    """List all completed appointments for a user (consultant's view)."""
    return list(
        session.exec(
            select(Appointment)
            .where(Appointment.user_id == user_id)
            .where(Appointment.status == AppointmentStatus.completed)
            .order_by(Appointment.scheduled_start_at.desc())
        ).all()
    )
