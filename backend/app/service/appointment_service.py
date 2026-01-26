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
    SessionStatus
)
from app.models.user import User, UserType


def _utc_now():
    return datetime.now(timezone.utc)


def _ensure_consultant(session: Session, consultant_user_id: int) -> User:
    u = session.get(User, consultant_user_id)
    if not u:
        raise HTTPException(status_code=404, detail="Consultant not found")
    if u.user_type != UserType.consultant:
        raise HTTPException(status_code=400, detail="Target user is not a consultant")
    return u


def apply_for_appointment(
    session: Session,
    *,
    user_id: int,
    consultant_user_id: int,
    note_from_user: Optional[str],
) -> AppointmentApplication:
    _ensure_consultant(session, consultant_user_id)

    now = _utc_now()
    app = AppointmentApplication(
        user_id=user_id,
        consultant_user_id=consultant_user_id,
        note_from_user=note_from_user,
        status=ApplicationStatus.submitted,
        created_at=now,
        updated_at=now,
    )
    session.add(app)
    session.commit()
    session.refresh(app)
    return app


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
    app = session.get(AppointmentApplication, application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    if app.consultant_user_id != consultant_user_id:
        raise HTTPException(status_code=403, detail="Not your application")
    if app.status != ApplicationStatus.submitted:
        raise HTTPException(status_code=400, detail="Application is not in submitted state")

    app.status = ApplicationStatus.rejected
    app.updated_at = _utc_now()
    session.add(app)
    session.commit()
    session.refresh(app)
    return app


def accept_and_schedule(
    session: Session,
    consultant_user_id: int,
    application_id: int,
    scheduled_start_at: datetime,
    scheduled_end_at: datetime,
) -> tuple[AppointmentApplication, Appointment, SessionRoom]:
    app = session.get(AppointmentApplication, application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    if app.consultant_user_id != consultant_user_id:
        raise HTTPException(status_code=403, detail="Not your application")
    if app.status != ApplicationStatus.submitted:
        raise HTTPException(status_code=400, detail="Application is not in submitted state")
    # Ensure naive UTC storage
    if scheduled_start_at.tzinfo is not None:
        scheduled_start_at = scheduled_start_at.astimezone(timezone.utc).replace(tzinfo=None)
    if scheduled_end_at.tzinfo is not None:
        scheduled_end_at = scheduled_end_at.astimezone(timezone.utc).replace(tzinfo=None)

    if scheduled_end_at <= scheduled_start_at:
        raise HTTPException(status_code=400, detail="scheduled_end_at must be after scheduled_start_at")

    now = _utc_now().replace(tzinfo=None) # store naive
    app.status = ApplicationStatus.accepted
    app.updated_at = now
    session.add(app)

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
    session.commit()
    session.refresh(appt)
    
    # Refresh adds it back, if naive in DB, it's naive here.

    room = SessionRoom(
        appointment_id=appt.id,
        status=SessionStatus.not_started,  
        created_at=now,
        updated_at=now,
    )

    session.add(room)
    session.commit()
    session.refresh(app)
    session.refresh(room)
    
    # Ensure returned appointment has timezone info for correct JSON serialization
    appt.scheduled_start_at = appt.scheduled_start_at.replace(tzinfo=timezone.utc)
    appt.scheduled_end_at = appt.scheduled_end_at.replace(tzinfo=timezone.utc)
    
    return app, appt, room


def list_my_appointments(session: Session, user_id: int) -> list[Appointment]:
    appts = session.exec(
        select(Appointment)
        .where(Appointment.user_id == user_id)
        .order_by(Appointment.scheduled_start_at.desc())
    ).all()
    
    # Ensure timezone awareness
    for a in appts:
        if a.scheduled_start_at.tzinfo is None:
            a.scheduled_start_at = a.scheduled_start_at.replace(tzinfo=timezone.utc)
        if a.scheduled_end_at.tzinfo is None:
            a.scheduled_end_at = a.scheduled_end_at.replace(tzinfo=timezone.utc)
            
    return list(appts)


def list_consultant_appointments(session: Session, consultant_user_id: int):
    from app.models.user_data import UserData
    from app.models.appointments import SessionRoom
    # Join with SessionRoom to get status
    results = session.exec(
        select(Appointment, User, UserData, SessionRoom.status)
        .join(User, Appointment.user_id == User.id)
        .join(UserData, Appointment.user_id == UserData.user_id, isouter=True)
        .join(SessionRoom, Appointment.id == SessionRoom.appointment_id, isouter=True)
        .where(Appointment.consultant_user_id == consultant_user_id)
        .order_by(Appointment.scheduled_start_at.desc())
    ).all()
    
    # Map to schema-compatible dict
    out = []
    for appt, user, user_data, session_status in results:
        d = appt.model_dump()
        # Ensure UTC
        if appt.scheduled_start_at.tzinfo is None:
            d['scheduled_start_at'] = appt.scheduled_start_at.replace(tzinfo=timezone.utc)
        if appt.scheduled_end_at.tzinfo is None:
            d['scheduled_end_at'] = appt.scheduled_end_at.replace(tzinfo=timezone.utc)
            
        out.append({
            **d, 
            "user": user, 
            "user_data": user_data,
            "session_status": session_status or SessionStatus.not_started
        })
        
    return out


def get_room_for_appointment(session: Session, appointment_id: int) -> SessionRoom:
    room = session.exec(select(SessionRoom).where(SessionRoom.appointment_id == appointment_id)).first()
    if not room:
        raise HTTPException(status_code=404, detail="Session room not found")
    return room
