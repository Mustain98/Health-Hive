from datetime import date
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.core.database import get_session
from app.core.auth import get_current_user
from app.modules.user.models import User
from app.modules.daily_goal.schemas import DailyGoalCreate, DailyGoalUpdate, DailyGoalRead
from app.modules.daily_log.schemas import DailyLogSubmit
from app.modules.daily_goal import services as svc

daily_goal_router = APIRouter(prefix="/daily-goals", tags=["Daily Goals"])


@daily_goal_router.get("/me", response_model=list[DailyGoalRead])
def list_my_daily_goals(
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    return svc.list_daily_goals(session, me.id)


@daily_goal_router.post("/me", response_model=DailyGoalRead)
def create_my_daily_goal(
    payload: DailyGoalCreate,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    return svc.create_daily_goal(session, me.id, payload)


# Static paths before the dynamic /{id} routes.
@daily_goal_router.get("/today")
def get_today(
    date_: Optional[date] = Query(default=None, alias="date"),
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """Today's daily log form (client passes its local `date`)."""
    return svc.get_today(session, me.id, date_)


@daily_goal_router.get("/history")
def get_log_history(
    start: Optional[date] = Query(default=None),
    end: Optional[date] = Query(default=None),
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """Per-day log history across all goals (default: last 30 days)."""
    return svc.get_log_history(session, me.id, start, end)


@daily_goal_router.post("/log")
def submit_log(
    payload: DailyLogSubmit,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    return svc.submit_log(session, me.id, payload)


@daily_goal_router.patch("/{daily_goal_id}", response_model=DailyGoalRead)
def update_daily_goal(
    daily_goal_id: uuid.UUID,
    payload: DailyGoalUpdate,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    return svc.update_daily_goal(session, me.id, daily_goal_id, payload)


@daily_goal_router.patch("/{daily_goal_id}/activate", response_model=DailyGoalRead)
def activate_daily_goal(
    daily_goal_id: uuid.UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    return svc.set_active(session, me.id, daily_goal_id, True)


@daily_goal_router.patch("/{daily_goal_id}/deactivate", response_model=DailyGoalRead)
def deactivate_daily_goal(
    daily_goal_id: uuid.UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    return svc.set_active(session, me.id, daily_goal_id, False)


@daily_goal_router.delete("/{daily_goal_id}")
def delete_daily_goal(
    daily_goal_id: uuid.UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    svc.delete_daily_goal(session, me.id, daily_goal_id)
    return {"ok": True}


@daily_goal_router.get("/{daily_goal_id}/logs")
def get_daily_goal_logs(
    daily_goal_id: uuid.UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    return svc.get_logs(session, me.id, daily_goal_id)
