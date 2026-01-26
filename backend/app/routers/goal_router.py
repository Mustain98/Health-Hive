from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.database import get_session
from app.core.auth import get_current_user
from app.models.user import User
from app.schemas.user_goal import GoalUpsert, GoalRead
from app.controller.goal_controller import get_my_goal, upsert_my_goal, delete_my_goal


goal_router = APIRouter(prefix="/goal", tags=["Goal"])


@goal_router.get("/me", response_model=GoalRead)
def read_goal_me(
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    return get_my_goal(session, me.id)


@goal_router.put("/me", response_model=GoalRead)
def upsert_goal_me(
    payload: GoalUpsert,
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
