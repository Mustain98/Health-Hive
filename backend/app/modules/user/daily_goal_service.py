"""Daily goals (habits that drive a milestone) + the daily log form.

Unlike milestones/targets/settings there is NO single-active constraint — a user
runs several daily habits at once. Risk is checked on any create-active/activate
(decision 3). The daily form is authoritative for calorie balance (decision 8) and
keyed on the client's local date (decision 10).
"""
from datetime import datetime, timezone, date, time, timedelta
from typing import Optional
import uuid

from fastapi import HTTPException
from sqlmodel import Session, select, delete

from app.modules.user.models import DailyGoal, DailyGoalLog, DailyLog
from app.modules.user.schemas import (
    DailyGoalCreate, DailyGoalUpdate, DailyLogSubmit, validate_daily_goal_attributes,
)
from app.modules.user.risk import assert_safe_daily_goal
from app.utils.text import short
from app.modules.notification import service as notif_service
from app.modules.notification.models import NotificationType


def _now() -> datetime:
    return datetime.now(timezone.utc)


def dedup_key(goal_type, name: Optional[str]) -> tuple[str, str]:
    """Identity for deduping habits: same type + same (case/space-insensitive) name."""
    gt = goal_type.value if hasattr(goal_type, "value") else str(goal_type)
    return (gt, (name or "").strip().lower())


def _day_start(d: date) -> datetime:
    return datetime.combine(d, time.min).replace(tzinfo=timezone.utc)


def _for_day(model, user_id: uuid.UUID, d: date):
    """Build a WHERE spanning the given calendar day for a model with .user_id/.date."""
    start = _day_start(d)
    return (model.user_id == user_id) & (model.date >= start) & (model.date < start + timedelta(days=1))


# ── CRUD ────────────────────────────────────────────────────────────────────

def create_daily_goal(session: Session, user_id: uuid.UUID, payload: DailyGoalCreate,
                      created_by: Optional[uuid.UUID] = None) -> DailyGoal:
    try:
        attrs = validate_daily_goal_attributes(payload.goal_type, payload.attributes)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Invalid attributes: {e}")

    dg = DailyGoal(
        created_for=user_id,
        created_by=created_by or user_id,
        milestone_id=payload.milestone_id,
        goal_type=payload.goal_type,
        name=short(payload.name, 120),
        target_value=payload.target_value,
        unit=short(payload.unit),
        active=payload.active,
        days_of_week=payload.days_of_week,
        attributes=attrs,
    )
    if dg.active:
        assert_safe_daily_goal(session, user_id, dg)  # activating = must be safe
    session.add(dg)
    session.commit()
    session.refresh(dg)
    return dg


def list_daily_goals(session: Session, user_id: uuid.UUID) -> list[DailyGoal]:
    return list(session.exec(
        select(DailyGoal).where(DailyGoal.created_for == user_id).order_by(DailyGoal.created_at.desc())
    ).all())


def _owned(session: Session, user_id: uuid.UUID, daily_goal_id: uuid.UUID) -> DailyGoal:
    dg = session.get(DailyGoal, daily_goal_id)
    if not dg or dg.created_for != user_id:
        raise HTTPException(status_code=404, detail="Daily goal not found")
    return dg


def set_active(session: Session, user_id: uuid.UUID, daily_goal_id: uuid.UUID, active: bool) -> DailyGoal:
    dg = _owned(session, user_id, daily_goal_id)
    if active:
        assert_safe_daily_goal(session, user_id, dg)
    dg.active = active
    dg.updated_at = _now()
    session.add(dg)
    session.commit()
    session.refresh(dg)
    return dg


def update_daily_goal(session: Session, user_id: uuid.UUID, daily_goal_id: uuid.UUID,
                      payload: DailyGoalUpdate) -> DailyGoal:
    dg = _owned(session, user_id, daily_goal_id)
    data = payload.model_dump(exclude_unset=True)
    if data.get("goal_type") is not None:
        dg.goal_type = data["goal_type"]
    for f in ("name", "target_value", "unit", "milestone_id", "days_of_week"):
        if f in data:
            setattr(dg, f, short(data[f], 120) if f in ("name", "unit") else data[f])
    if data.get("attributes") is not None:
        try:
            dg.attributes = validate_daily_goal_attributes(dg.goal_type, data["attributes"])
        except ValueError as e:
            raise HTTPException(status_code=422, detail=f"Invalid attributes: {e}")
    if data.get("active") is not None:
        dg.active = data["active"]
    if dg.active:
        assert_safe_daily_goal(session, user_id, dg)  # edited value must still be safe
    dg.updated_at = _now()
    session.add(dg)
    session.commit()
    session.refresh(dg)
    return dg


def delete_daily_goal(session: Session, user_id: uuid.UUID, daily_goal_id: uuid.UUID) -> None:
    dg = _owned(session, user_id, daily_goal_id)
    session.exec(delete(DailyGoalLog).where(DailyGoalLog.daily_goal_id == daily_goal_id))  # cascade
    session.delete(dg)
    session.commit()


def get_logs(session: Session, user_id: uuid.UUID, daily_goal_id: uuid.UUID) -> list[DailyGoalLog]:
    _owned(session, user_id, daily_goal_id)
    return list(session.exec(
        select(DailyGoalLog)
        .where(DailyGoalLog.daily_goal_id == daily_goal_id)
        .order_by(DailyGoalLog.date.asc())
    ).all())


def get_log_history(session: Session, user_id: uuid.UUID,
                    start: Optional[date] = None, end: Optional[date] = None) -> list[dict]:
    """Per-day log history across all goals (newest first). Default: last 30 days."""
    end = end or date.today()
    start = start or end - timedelta(days=29)
    start_dt, end_dt = _day_start(start), _day_start(end) + timedelta(days=1)

    goals = {g.id: g for g in list_daily_goals(session, user_id)}
    goal_logs = session.exec(
        select(DailyGoalLog).where(
            DailyGoalLog.user_id == user_id,
            DailyGoalLog.date >= start_dt, DailyGoalLog.date < end_dt)
    ).all()
    daily_logs = session.exec(
        select(DailyLog).where(
            DailyLog.user_id == user_id,
            DailyLog.date >= start_dt, DailyLog.date < end_dt)
    ).all()

    by_day: dict[str, list[dict]] = {}
    for l in goal_logs:
        g = goals.get(l.daily_goal_id)
        by_day.setdefault(l.date.date().isoformat(), []).append({
            "daily_goal_id": str(l.daily_goal_id),
            "name": g.name if g else "(deleted goal)",
            "goal_type": (g.goal_type.value if hasattr(g.goal_type, "value") else g.goal_type) if g else None,
            "target_value": g.target_value if g else None,
            "unit": g.unit if g else None,
            "completed": l.completed,
            "value": l.value,
        })
    daily_by_day = {dl.date.date().isoformat(): dl for dl in daily_logs}

    days = sorted(set(by_day) | set(daily_by_day), reverse=True)
    return [{
        "date": d,
        "goals": by_day.get(d, []),
        "calories_in": daily_by_day[d].calories_in if d in daily_by_day else None,
        "calories_out": daily_by_day[d].calories_out if d in daily_by_day else None,
        "deficit_surplus": daily_by_day[d].deficit_surplus if d in daily_by_day else None,
    } for d in days]


# ── Daily log form ──────────────────────────────────────────────────────────

def get_today(session: Session, user_id: uuid.UUID, day: Optional[date] = None) -> dict:
    """Return today's form (active goals + their log state + calorie balance),
    lazily materializing DailyGoalLog rows + a DailyLog + a one-per-day notification."""
    day = day or date.today()
    wd = day.weekday()  # Mon=0 … Sun=6
    # Only goals scheduled for this weekday (no schedule / empty = every day).
    scheduled_goals = [
        g for g in list_daily_goals(session, user_id)
        if g.active and (not g.days_of_week or wd in g.days_of_week)
    ]

    existing_logs = {
        l.daily_goal_id: l
        for l in session.exec(select(DailyGoalLog).where(_for_day(DailyGoalLog, user_id, day))).all()
    }
    for g in scheduled_goals:
        if g.id not in existing_logs:
            l = DailyGoalLog(daily_goal_id=g.id, user_id=user_id, date=_day_start(day), completed=False)
            session.add(l)
            existing_logs[g.id] = l

    daily_log = session.exec(select(DailyLog).where(_for_day(DailyLog, user_id, day))).first()
    daily_log_created = False
    if not daily_log:
        daily_log = DailyLog(user_id=user_id, date=_day_start(day))
        session.add(daily_log)
        daily_log_created = True

    # "Log your day" — once per day (anchored on first DailyLog creation).
    if daily_log_created and scheduled_goals:
        notif_service.create(
            session, user_id, NotificationType.daily_log,
            title="Log your day",
            body="Did you complete today's goals?",
            data={"date": day.isoformat()},
        )

    session.commit()

    return {
        "date": day.isoformat(),
        "daily_goals": [
            {
                "id": str(g.id), "name": g.name, "goal_type": g.goal_type,
                "target_value": g.target_value, "unit": g.unit, "attributes": g.attributes,
                "days_of_week": g.days_of_week,
                "completed": existing_logs[g.id].completed,
                "value": existing_logs[g.id].value,
            }
            for g in scheduled_goals
        ],
        "calories_in": daily_log.calories_in,
        "calories_out": daily_log.calories_out,
        "deficit_surplus": daily_log.deficit_surplus,
    }


def submit_log(session: Session, user_id: uuid.UUID, payload: DailyLogSubmit) -> dict:
    day = payload.date or date.today()

    existing = {
        l.daily_goal_id: l
        for l in session.exec(select(DailyGoalLog).where(_for_day(DailyGoalLog, user_id, day))).all()
    }
    for c in payload.completions:
        dg = session.get(DailyGoal, c.daily_goal_id)
        if not dg or dg.created_for != user_id:
            continue  # ignore goals that aren't the user's
        log = existing.get(c.daily_goal_id)
        if not log:
            log = DailyGoalLog(daily_goal_id=c.daily_goal_id, user_id=user_id, date=_day_start(day))
        log.completed = c.completed
        log.value = c.value
        session.add(log)

    daily_log = session.exec(select(DailyLog).where(_for_day(DailyLog, user_id, day))).first()
    if not daily_log:
        daily_log = DailyLog(user_id=user_id, date=_day_start(day))
    if payload.calories_in is not None:
        daily_log.calories_in = payload.calories_in
    if payload.calories_out is not None:
        daily_log.calories_out = payload.calories_out
    if daily_log.calories_in is not None and daily_log.calories_out is not None:
        daily_log.deficit_surplus = daily_log.calories_in - daily_log.calories_out
    daily_log.updated_at = _now()
    session.add(daily_log)

    session.commit()
    return {
        "date": day.isoformat(),
        "calories_in": daily_log.calories_in,
        "calories_out": daily_log.calories_out,
        "deficit_surplus": daily_log.deficit_surplus,
    }
