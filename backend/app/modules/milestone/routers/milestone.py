from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.database import get_session
from app.core.auth import get_current_user
from app.modules.user.models import User
from app.modules.milestone.models import Milestone
from app.modules.milestone.schemas import GoalDateChangeRequest
from app.modules.milestone.models import MilestoneLog
from app.modules.milestone.schemas import MilestoneLogCreate
from app.modules.milestone.controllers import get_my_goal, create_my_goal, delete_my_goal, get_my_all_goals
import uuid

goal_router = APIRouter(prefix="/goal", tags=["Goal"])


@goal_router.get("/me", response_model=Milestone)
def read_goal_me(
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    return get_my_goal(session, me.id)


@goal_router.get("/all", response_model=list[Milestone])
def read_all_goals_me(
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    return get_my_all_goals(session, me.id)


@goal_router.put("/me", response_model=Milestone)
def create_goal_for_user(
    payload: Milestone,
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
    from app.modules.milestone.services import delete_goal_by_id
    delete_goal_by_id(session, me.id, goal_id)
    return {"ok": True}


@goal_router.put("/{goal_id}/activate", response_model=Milestone)
def activate_goal_endpoint(
    goal_id: uuid.UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    from app.modules.milestone.controllers import activate_my_goal
    return activate_my_goal(session, me.id, goal_id)

from app.modules.milestone.services import change_goal_date
@goal_router.patch("/{goal_id}/change-date", response_model=Milestone)
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

@goal_router.post("/log", response_model=MilestoneLog)
def add_goal_log_endpoint(
    payload: MilestoneLogCreate,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    from app.modules.milestone.services import add_goal_log
    return add_goal_log(session, me.id, payload)


@goal_router.get("/{goal_id}/logs", response_model=list[MilestoneLog])
def get_goal_logs_endpoint(
    goal_id: uuid.UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    from app.modules.milestone.services import get_goal_logs
    return get_goal_logs(session, me.id, goal_id)
