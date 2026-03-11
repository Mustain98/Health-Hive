from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.core.database import get_session
from app.core.auth import get_current_user
from app.models.user import User
from app.models.user_goal import UserGoal, GoalDateChangeRequest, UserGoalRead
from app.models.user_data import UserGoalLog, UserGoalLogCreate
from app.controller.goal_controller import get_my_goal, create_my_goal, delete_my_goal, get_my_all_goals
import uuid

goal_router = APIRouter(prefix="/goal", tags=["Goal"])

def _to_read(session: Session, goal: UserGoal) -> UserGoalRead:
    res = UserGoalRead.model_validate(goal)
    if goal.created_by and goal.created_by != goal.created_for:
        creator = session.get(User, goal.created_by)
        if creator:
            res.created_by_name = creator.full_name or creator.username
            res.created_by_email = creator.email
    return res

@goal_router.get("/me", response_model=UserGoalRead)
def read_goal_me(
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    goal = get_my_goal(session, me.id)
    return _to_read(session, goal)


@goal_router.get("/all", response_model=list[UserGoalRead])
def read_all_goals_me(
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    goals = get_my_all_goals(session, me.id)
    return [_to_read(session, g) for g in goals]


@goal_router.put("/me", response_model=UserGoalRead)
def create_goal_for_user(
    payload: UserGoal,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    goal = create_my_goal(session, me.id, payload)
    return _to_read(session, goal)


@goal_router.delete("/me")
def delete_goal_me(
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    delete_my_goal(session, me.id)
    return {"ok": True}

@goal_router.put("/{goal_id}/activate", response_model=UserGoalRead)
def activate_goal_endpoint(
    goal_id: uuid.UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    from app.controller.goal_controller import activate_my_goal
    goal = activate_my_goal(session, me.id, goal_id)
    return _to_read(session, goal)

from app.service.user_goal_service import change_goal_date
@goal_router.patch("/{goal_id}/change-date", response_model=UserGoalRead)
def change_goal_date_route(
    goal_id: uuid.UUID,
    payload: GoalDateChangeRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    goal = change_goal_date(
        session=session,
        user_id=current_user.id,
        goal_id=goal_id,
        new_start_date=payload.new_start_date,
    )
    return _to_read(session, goal)

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
