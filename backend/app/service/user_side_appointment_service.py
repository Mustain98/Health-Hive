from __future__ import annotations

import uuid
from datetime import datetime, timezone, date, time, timedelta
from zoneinfo import ZoneInfo
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
from app.models.consultant import ConsultantProfile, ConsultantAvailabilityRule
from app.models.user import UserType, User


def utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _ensure_consultant(session: Session, consultant_user_id: uuid.UUID) -> User:
    u = session.get(User, consultant_user_id)
    if not u:
        raise HTTPException(404, "Consultant not found")
    if u.user_type != UserType.consultant:
        raise HTTPException(400, "Target user is not a consultant")
    return u


def _overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    return a_start < b_end and a_end > b_start


def _merge_intervals(intervals: list[tuple[datetime, datetime]]) -> list[tuple[datetime, datetime]]:
    if not intervals:
        return []
    intervals.sort(key=lambda x: x[0])
    merged = [intervals[0]]

    for s, e in intervals[1:]:
        last_s, last_e = merged[-1]
        if s <= last_e:  # overlap or touch
            merged[-1] = (last_s, max(last_e, e))
        else:
            merged.append((s, e))

    return merged


def _local_day_bounds_to_utc_naive(day: date, tz: ZoneInfo) -> tuple[datetime, datetime]:
    local_start = datetime.combine(day, time(0, 0)).replace(tzinfo=tz)
    local_end = local_start + timedelta(days=1)

    return (
        local_start.astimezone(timezone.utc).replace(tzinfo=None),
        local_end.astimezone(timezone.utc).replace(tzinfo=None),
    )


def get_free_windows_for_date(
    session: Session,
    *,
    consultant_user_id: uuid.UUID,
    target_date: date,      # consultant-local date
) -> list[tuple[datetime, datetime]]:
    """
    Returns list of (free_start_utc_naive, free_end_utc_naive) as UTC-naive datetimes.
    """
    _ensure_consultant(session, consultant_user_id)

    profile = session.exec(
        select(ConsultantProfile).where(ConsultantProfile.user_id == consultant_user_id)
    ).first()
    if not profile:
        raise HTTPException(404, "Consultant profile not found")

    rules = session.exec(
        select(ConsultantAvailabilityRule)
        .where(ConsultantAvailabilityRule.consultant_profile_id == profile.user_id)
        .where(ConsultantAvailabilityRule.is_active == True)
    ).all()
    if not rules:
        return []

    tz = ZoneInfo(rules[0].timezone)

    weekday = target_date.weekday()
    day_rules = [r for r in rules if int(r.day_of_week) == weekday and r.is_active]
    if not day_rules:
        return []

    day_start_utc, day_end_utc = _local_day_bounds_to_utc_naive(target_date, tz)

    appts = session.exec(
        select(Appointment)
        .where(Appointment.consultant_user_id == consultant_user_id)
        .where(Appointment.status == AppointmentStatus.scheduled)
        .where(Appointment.scheduled_start_at < day_end_utc)
        .where(Appointment.scheduled_end_at > day_start_utc)
        .order_by(Appointment.scheduled_start_at)
    ).all()

    busy_all = [(a.scheduled_start_at, a.scheduled_end_at) for a in appts]

    free_windows: list[tuple[datetime, datetime]] = []

    for rule in day_rules:
        min_delta = timedelta(minutes=rule.consultation_duration)
        local_start = datetime.combine(target_date, rule.start_time).replace(tzinfo=tz)
        local_end = datetime.combine(target_date, rule.end_time).replace(tzinfo=tz)

        win_start = local_start.astimezone(timezone.utc).replace(tzinfo=None)
        win_end = local_end.astimezone(timezone.utc).replace(tzinfo=None)

        if win_end <= win_start:
            continue

        busy: list[tuple[datetime, datetime]] = []
        for bs, be in busy_all:
            if _overlaps(bs, be, win_start, win_end):
                busy.append((max(bs, win_start), min(be, win_end)))

        busy = _merge_intervals(busy)

        cursor = win_start

        if not busy:
            if win_end - win_start >= min_delta:
                free_windows.append((win_start, win_end))
            continue

        for bs, be in busy:
            if cursor < bs:
                gap_start, gap_end = cursor, bs
                if gap_end - gap_start >= min_delta:
                    free_windows.append((gap_start, gap_end))
            cursor = max(cursor, be)

        if cursor < win_end:
            gap_start, gap_end = cursor, win_end
            if gap_end - gap_start >= min_delta:
                free_windows.append((gap_start, gap_end))

    return free_windows


def apply_for_appointment(
    session: Session,
    *,
    user_id: uuid.UUID,
    consultant_user_id: uuid.UUID,
    requested_start_at: datetime,
    note_from_user: Optional[str] = None,
) -> AppointmentApplication:
    _ensure_consultant(session, consultant_user_id)

    # normalize to naive UTC
    if requested_start_at.tzinfo is not None:
        requested_start_at = requested_start_at.astimezone(timezone.utc).replace(tzinfo=None)

    now = utc_now_naive()
    if requested_start_at < now:
        raise HTTPException(400, "Cannot request a time in the past")

    # basic conflict guard: requested start cannot be inside an existing appointment
    conflict = session.exec(
        select(Appointment)
        .where(Appointment.consultant_user_id == consultant_user_id)
        .where(Appointment.status == AppointmentStatus.scheduled)
        .where(Appointment.scheduled_start_at <= requested_start_at)
        .where(Appointment.scheduled_end_at > requested_start_at)
    ).first()
    if conflict:
        raise HTTPException(409, "This time is no longer available")

    app = AppointmentApplication(
        user_id=user_id,
        consultant_user_id=consultant_user_id,
        requested_start_at=requested_start_at,
        note_from_user=note_from_user,
        status=ApplicationStatus.submitted,
        created_at=now,
        updated_at=now,
    )
    session.add(app)
    session.commit()
    session.refresh(app)
    return app


def user_accept_proposal(
    session: Session,
    *,
    user_id: uuid.UUID,
    application_id: uuid.UUID,
) -> AppointmentApplication:
    app = session.get(AppointmentApplication, application_id)
    if not app:
        raise HTTPException(404, "Application not found")
    if app.user_id != user_id:
        raise HTTPException(403, "Not your application")
    if app.status != ApplicationStatus.proposed:
        raise HTTPException(400, "No proposal to accept")
    if not app.proposed_start_at:
        raise HTTPException(400, "Proposal time missing")

    now = utc_now_naive()
    if app.proposed_start_at < now:
        raise HTTPException(400, "Proposed time is in the past")

    app.status = ApplicationStatus.proposal_accepted
    app.proposal_accepted_at = now
    app.updated_at = now

    session.add(app)
    session.commit()
    session.refresh(app)
    return app


def cancel_application(session: Session, *, user_id: uuid.UUID, application_id: uuid.UUID) -> AppointmentApplication:
    app = session.get(AppointmentApplication, application_id)
    if not app:
        raise HTTPException(404, "Application not found")
    if app.user_id != user_id:
        raise HTTPException(403, "Not your application")

    # once scheduled, user must cancel the appointment instead
    if app.status == ApplicationStatus.scheduled:
        raise HTTPException(400, "Already scheduled. Cancel the appointment instead.")

    if app.status in (ApplicationStatus.rejected, ApplicationStatus.cancelled):
        raise HTTPException(400, "Application is not cancellable")

    now = utc_now_naive()
    app.status = ApplicationStatus.cancelled
    app.updated_at = now

    session.add(app)
    session.commit()
    session.refresh(app)
    return app


def cancel_appointment(session: Session, *, user_id: uuid.UUID, appointment_id: uuid.UUID) -> Appointment:
    appt = session.get(Appointment, appointment_id)
    if not appt:
        raise HTTPException(404, "Appointment not found")
    if appt.user_id != user_id:
        raise HTTPException(403, "Not your appointment")
    if appt.status != AppointmentStatus.scheduled:
        raise HTTPException(400, "Only scheduled appointments can be cancelled")

    now = utc_now_naive()
    appt.status = AppointmentStatus.cancelled
    appt.updated_at = now
    session.add(appt)

    room = session.exec(select(SessionRoom).where(SessionRoom.appointment_id == appointment_id)).first()
    if room:
        room.status = SessionStatus.ended
        room.ended_at = now
        room.ended_by_user_id = user_id
        room.updated_at = now
        session.add(room)

    session.commit()
    session.refresh(appt)
    return appt
