from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.database import get_session
from app.core.auth import get_current_user
from app.modules.user.models import User
from app.modules.user.models import  UserGoal,GoalDateChangeRequest
from app.modules.user.models import UserGoalLog, UserGoalLogCreate
from app.modules.user.goal_controller import get_my_goal, create_my_goal, delete_my_goal, get_my_all_goals
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
def create_goal_for_user(
    payload: UserGoal,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    return create_my_goal(session, me.id, payload)


@goal_router.delete("/me")
def delete_goal_me(
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    delete_my_goal(session, me.id)
    return {"ok": True}

@goal_router.delete("/{goal_id}")
def delete_goal_by_id_endpoint(
    goal_id: uuid.UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    from app.modules.user.user_goal_service import delete_goal_by_id
    delete_goal_by_id(session, me.id, goal_id)
    return {"ok": True}


@goal_router.put("/{goal_id}/activate", response_model=UserGoal)
def activate_goal_endpoint(
    goal_id: uuid.UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    from app.modules.user.goal_controller import activate_my_goal
    return activate_my_goal(session, me.id, goal_id)

from app.modules.user.user_goal_service import change_goal_date
@goal_router.patch("/{goal_id}/change-date", response_model=UserGoal)
def change_goal_date_route(
    goal_id: uuid.UUID,
    payload: GoalDateChangeRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return change_goal_date(
        session=session,
        user_id=current_user.id,
        goal_id=goal_id,
        new_start_date=payload.new_start_date,
    )

@goal_router.post("/log", response_model=UserGoalLog)
def add_goal_log_endpoint(
    payload: UserGoalLogCreate,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    from app.modules.user.user_goal_service import add_goal_log
    return add_goal_log(session, me.id, payload)


@goal_router.get("/{goal_id}/logs", response_model=list[UserGoalLog])
def get_goal_logs_endpoint(
    goal_id: uuid.UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    from app.modules.user.user_goal_service import get_goal_logs
    return get_goal_logs(session, me.id, goal_id)
