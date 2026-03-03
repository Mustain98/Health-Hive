from __future__ import annotations

from datetime import datetime, timezone, date
from typing import Optional
import uuid

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models.appointments import (
    AppointmentApplication,
    ApplicationStatus,
    Appointment,
    AppointmentStatus,
    SessionRoom,
    SessionStatus,
    AppointmentWithParticipants,
)
from app.models.user import User, UserType
from app.models.user_data import UserData
from app.models.user_goal import UserGoal
from app.models.nutrition_target import NutritionTarget


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


def list_user_history(session: Session, user_id: uuid.UUID) -> list[Appointment]:
    """List all completed appointments for a user."""
    return list(
        session.exec(
            select(Appointment)
            .where(Appointment.user_id == user_id)
            .where(Appointment.status == AppointmentStatus.completed)
            .order_by(Appointment.scheduled_start_at.desc())
        ).all()
    )


def search_my_appointments(
    session: Session,
    user_id: uuid.UUID,
    date: Optional[date] = None,
    consultant_name: Optional[str] = None
) -> list[Appointment]:
    query = select(Appointment).where(Appointment.user_id == user_id)

    if date:
        # Filter by scheduled_start_at date
        # Assuming scheduled_start_at is datetime
        from datetime import datetime, time, timedelta
        # Naive UTC construction for start/end of day
        # NOTE: This simple date filter assumes UTC dates. 
        # Ideally we should handle client timezone, but for now exact date match on UTC day.
        start_of_day = datetime.combine(date, time.min)
        end_of_day = datetime.combine(date, time.max)
        query = query.where(Appointment.scheduled_start_at >= start_of_day).where(Appointment.scheduled_start_at <= end_of_day)

    if consultant_name:
        # Join with User to filter by consultant name
        query = query.join(User, Appointment.consultant_user_id == User.id)
        # Case insensitive search on full_name or username
        term = f"%{consultant_name}%"
        query = query.where(
            (User.full_name.ilike(term)) | (User.username.ilike(term))
        )
    
    query = query.order_by(Appointment.scheduled_start_at.desc())
    return list(session.exec(query).all())


def get_appointment_details_with_extras(
    session: Session,
    user_id: uuid.UUID,
    appointment_id: uuid.UUID,
    is_consultant: bool = False,
) -> tuple[Appointment, Optional[UserGoal], Optional[NutritionTarget], Optional[User]]:
    """Return appointment extras (goal, nutrition_target, consultant user).

    Works for both patient (is_consultant=False) and consultant (is_consultant=True).
    """
    appt = session.get(Appointment, appointment_id)
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    # Ownership check differs by role
    if is_consultant:
        if appt.consultant_user_id != user_id:
            raise HTTPException(status_code=403, detail="Not your appointment")
    else:
        if appt.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not your appointment")

    # Fetch linked Goal
    from app.models.user_goal import UserGoal
    goal = session.exec(select(UserGoal).where(UserGoal.appointment_id == appointment_id)).first()

    # Fetch linked Target
    from app.models.nutrition_target import NutritionTarget
    target = session.exec(select(NutritionTarget).where(NutritionTarget.appointment_id == appointment_id)).first()

    # Fetch Consultant info
    consultant = session.get(User, appt.consultant_user_id)

    return appt, goal, target, consultant


def consultant_search_appointments(
    session: Session,
    consultant_user_id: uuid.UUID,
    date: Optional[date] = None,
    patient_name: Optional[str] = None
) -> list[Appointment]:
    # Consultant can only see appointments with them.
    query = select(Appointment).where(Appointment.consultant_user_id == consultant_user_id)

    # 1. Date Filter
    if date:
        from datetime import datetime, time
        start_of_day = datetime.combine(date, time.min)
        end_of_day = datetime.combine(date, time.max)
        query = query.where(Appointment.scheduled_start_at >= start_of_day).where(Appointment.scheduled_start_at <= end_of_day)

    # 2. Patient Name Filter
    if patient_name:
        query = query.join(User, Appointment.user_id == User.id)
        term = f"%{patient_name}%"
        query = query.where(
            (User.full_name.ilike(term)) | (User.username.ilike(term)) | (User.email.ilike(term))
        )
    
    # 3. Permission Check? 
    # The requirement says: "consultant can filter and search appointment... once user revoke consultant cant see"
    # So we filter by consultant_access=True
    query = query.where(Appointment.consultant_access == True)

    query = query.order_by(Appointment.scheduled_start_at.desc())
    return list(session.exec(query).all())


def _enrich_appointments_with_participants(
    session: Session,
    appointments: list[Appointment],
    perspective: str,  # "user" or "consultant"
) -> list[AppointmentWithParticipants]:
    """
    Given a list of Appointment rows, fetch the required User/ConsultantProfile rows
    and build AppointmentWithParticipants objects.  No aliased() needed.
    """
    from app.models.consultant import ConsultantProfile

    if not appointments:
        return []

    # Collect all the IDs we need to look up
    user_ids = {a.user_id for a in appointments}
    consultant_ids = {a.consultant_user_id for a in appointments}
    all_ids = user_ids | consultant_ids
    appt_ids = [a.id for a in appointments]

    # Batch load users
    users: dict[uuid.UUID, User] = {
        u.id: u
        for u in session.exec(select(User).where(User.id.in_(list(all_ids)))).all()
    }

    # Batch load consultant profiles
    profiles: dict[uuid.UUID, ConsultantProfile] = {
        p.user_id: p
        for p in session.exec(
            select(ConsultantProfile).where(ConsultantProfile.user_id.in_(list(consultant_ids)))
        ).all()
    }

    # Batch load session rooms
    rooms: dict[uuid.UUID, str] = {
        r.appointment_id: r.status
        for r in session.exec(
            select(SessionRoom).where(SessionRoom.appointment_id.in_(appt_ids))
        ).all()
    }

    results = []
    for appt in appointments:
        patient = users.get(appt.user_id)
        c_user = users.get(appt.consultant_user_id)
        c_profile = profiles.get(appt.consultant_user_id)

        results.append(
            AppointmentWithParticipants(
                **appt.model_dump(),
                user_name=patient.full_name or patient.username if patient else None,
                user_email=patient.email if patient else None,
                consultant_name=(
                    c_profile.display_name if c_profile
                    else (c_user.full_name or c_user.username if c_user else None)
                ),
                consultant_email=c_user.email if c_user else None,
                session_status=rooms.get(appt.id),
            )
        )
    return results


def search_my_appointments_with_participants(
    session: Session,
    user_id: uuid.UUID,
    date: Optional[date] = None,
    consultant_name: Optional[str] = None,
) -> list[AppointmentWithParticipants]:
    """Fetch user's appointments and enrich with participant display info."""
    from app.models.consultant import ConsultantProfile

    query = select(Appointment).where(Appointment.user_id == user_id)

    if date:
        from datetime import time as dt_time
        start_of_day = datetime.combine(date, dt_time.min)
        end_of_day = datetime.combine(date, dt_time.max)
        query = query.where(
            Appointment.scheduled_start_at >= start_of_day,
            Appointment.scheduled_start_at <= end_of_day,
        )

    query = query.order_by(Appointment.scheduled_start_at.desc())
    appointments = list(session.exec(query).all())

    # Filter by consultant name (in-memory, after fetching profile data)
    if consultant_name and appointments:
        consultant_ids = {a.consultant_user_id for a in appointments}
        term = consultant_name.lower()

        c_users: dict[uuid.UUID, User] = {
            u.id: u for u in session.exec(
                select(User).where(User.id.in_(list(consultant_ids)))
            ).all()
        }
        c_profiles: dict[uuid.UUID, ConsultantProfile] = {
            p.user_id: p for p in session.exec(
                select(ConsultantProfile).where(ConsultantProfile.user_id.in_(list(consultant_ids)))
            ).all()
        }
        appointments = [
            a for a in appointments
            if term in (c_profiles.get(a.consultant_user_id, None) and
                        c_profiles[a.consultant_user_id].display_name or "").lower()
            or term in (c_users.get(a.consultant_user_id) and
                        (c_users[a.consultant_user_id].full_name or "")).lower()
            or term in (c_users.get(a.consultant_user_id) and
                        c_users[a.consultant_user_id].username or "").lower()
        ]

    return _enrich_appointments_with_participants(session, appointments, perspective="user")


def consultant_search_appointments_with_participants(
    session: Session,
    consultant_user_id: uuid.UUID,
    date: Optional[date] = None,
    patient_name: Optional[str] = None,
) -> list[AppointmentWithParticipants]:
    """Fetch consultant's appointments and enrich with patient display info."""
    query = (
        select(Appointment)
        .where(Appointment.consultant_user_id == consultant_user_id)
        .where(Appointment.consultant_access == True)
    )

    if date:
        from datetime import time as dt_time
        start_of_day = datetime.combine(date, dt_time.min)
        end_of_day = datetime.combine(date, dt_time.max)
        query = query.where(
            Appointment.scheduled_start_at >= start_of_day,
            Appointment.scheduled_start_at <= end_of_day,
        )

    query = query.order_by(Appointment.scheduled_start_at.desc())
    appointments = list(session.exec(query).all())

    # Filter by patient name in-memory
    if patient_name and appointments:
        user_ids = {a.user_id for a in appointments}
        term = patient_name.lower()
        p_users: dict[uuid.UUID, User] = {
            u.id: u for u in session.exec(
                select(User).where(User.id.in_(list(user_ids)))
            ).all()
        }
        appointments = [
            a for a in appointments
            if term in (p_users.get(a.user_id) and
                        (p_users[a.user_id].full_name or "")).lower()
            or term in (p_users.get(a.user_id) and
                        p_users[a.user_id].username or "").lower()
            or term in (p_users.get(a.user_id) and
                        p_users[a.user_id].email or "").lower()
        ]

    return _enrich_appointments_with_participants(session, appointments, perspective="consultant")
def toggle_appointment_permission(
    session: Session,
    user_id: uuid.UUID,
    appointment_id: uuid.UUID,
    grant: bool
) -> Appointment:
    appt = session.get(Appointment, appointment_id)
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if appt.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not your appointment")
    
    appt.consultant_access = grant
    session.add(appt)
    session.commit()
    session.refresh(appt)
    return appt
