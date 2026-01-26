from datetime import datetime, timezone

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models.user_goal import UserGoal
from app.schemas.user_goal import GoalUpsert


def _utc_now():
    return datetime.now(timezone.utc)


def get_goal_for_user(session: Session, user_id: int) -> UserGoal:
    goal = session.exec(select(UserGoal).where(UserGoal.user_id == user_id)).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return goal


def upsert_goal_for_user(session: Session, user_id: int, payload: GoalUpsert) -> UserGoal:
    goal = session.exec(select(UserGoal).where(UserGoal.user_id == user_id)).first()
    data = payload.model_dump(exclude_unset=True)

    if not goal:
        goal = UserGoal(user_id=user_id, **data)
        goal.created_at = _utc_now()
        goal.updated_at = _utc_now()
        session.add(goal)
    else:
        for k, v in data.items():
            setattr(goal, k, v)
        goal.updated_at = _utc_now()
        session.add(goal)

    session.commit()
    session.refresh(goal)
    return goal


def delete_goal_for_user(session: Session, user_id: int) -> None:
    goal = session.exec(select(UserGoal).where(UserGoal.user_id == user_id)).first()
    if not goal:
        return
    session.delete(goal)
    session.commit()
