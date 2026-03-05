from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.database import get_session
from app.core.auth import get_current_user
from app.models.user import User
from app.models.user_goal import  UserGoal
from app.models.user_data import UserGoalLog, UserGoalLogCreate
from app.controller.goal_controller import get_my_goal, upsert_my_goal, delete_my_goal, get_my_all_goals
import uuid

goal_router = APIRouter(prefix="/goal", tags=["Goal"])


@goal_router.get("/me", response_model=UserGoal)
def read_goal_me(
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    return get_my_goal(session, me.id)


@goal_router.get("/all", response_model=list[UserGoal])
def read_all_goals_me(
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    return get_my_all_goals(session, me.id)


@goal_router.put("/me", response_model=UserGoal)
def upsert_goal_me(
    payload: UserGoal,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    return upsert_my_goal(session, me.id, payload)


@goal_router.delete("/me")
def delete_goal_me(
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    delete_my_goal(session, me.id)
    return {"ok": True}
@goal_router.put("/{goal_id}/activate", response_model=UserGoal)
def activate_goal_endpoint(
    goal_id: uuid.UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    from app.controller.goal_controller import activate_my_goal
    return activate_my_goal(session, me.id, goal_id)


@goal_router.post("/log", response_model=UserGoalLog)
def add_goal_log_endpoint(
    payload: UserGoalLogCreate,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    from app.service.user_goal_service import add_goal_log
    return add_goal_log(session, me.id, payload)


@goal_router.get("/{goal_id}/logs", response_model=list[UserGoalLog])
def get_goal_logs_endpoint(
    goal_id: uuid.UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    from app.service.user_goal_service import get_goal_logs
    return get_goal_logs(session, me.id, goal_id)
