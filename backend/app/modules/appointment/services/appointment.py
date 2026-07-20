from __future__ import annotations

from datetime import datetime, timezone, date
from typing import Optional
import uuid

from fastapi import HTTPException
from sqlmodel import Session, select

from app.modules.appointment.models import Appointment, AppointmentStatus, SessionRoom, SessionStatus
from app.modules.appointment.schemas import AppointmentWithParticipants
from app.modules.user.models import User
from app.modules.user.schemas import UserType
from app.modules.user.models import UserData
from app.modules.milestone.models import Milestone
from app.modules.nutrition_target.models import NutritionTarget


def utc_now_naive() -> datetime:
    """Always store naive UTC in DB."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def get_room_for_appointment(session: Session, appointment_id: int) -> SessionRoom:
    room = session.exec(select(SessionRoom).where(SessionRoom.appointment_id == appointment_id)).first()
    if not room:
        raise HTTPException(404, "Session room not found")
    return room


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


from app.modules.meal_plan_setting.models import MealPlanSetting

def get_appointment_details_with_extras(
    session: Session,
    user_id: uuid.UUID,
    appointment_id: uuid.UUID,
    is_consultant: bool = False,
) -> tuple[Appointment, Optional[Milestone], Optional[NutritionTarget], Optional[MealPlanSetting], Optional[User]]:
    """Return appointment extras (goal, nutrition_target, meal_plan_setting, consultant user).

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
    from app.modules.milestone.models import Milestone
    goal = session.exec(select(Milestone).where(Milestone.appointment_id == appointment_id)).first()

    # Fetch linked Target
    from app.modules.nutrition_target.models import NutritionTarget
    target = session.exec(select(NutritionTarget).where(NutritionTarget.appointment_id == appointment_id)).first()

    # Fetch linked Meal Plan Setting
    meal_setting = session.exec(select(MealPlanSetting).where(MealPlanSetting.appointment_id == appointment_id)).first()

    # Fetch Consultant info
    consultant = session.get(User, appt.consultant_user_id)

    return appt, goal, target, meal_setting, consultant


def _enrich_appointments_with_participants(
    session: Session,
    appointments: list[Appointment],
    perspective: str,  # "user" or "consultant"
) -> list[AppointmentWithParticipants]:
    """
    Given a list of Appointment rows, fetch the required User/ConsultantProfile rows
    and build AppointmentWithParticipants objects.  No aliased() needed.
    """
    from app.modules.consultant.models import ConsultantProfile

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
    from app.modules.consultant.models import ConsultantProfile

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
