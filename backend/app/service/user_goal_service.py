from datetime import datetime, timezone

from fastapi import HTTPException
from sqlmodel import Session, select
import uuid
from typing import Optional

from app.models.user_goal import UserGoal




def get_goal_for_user(session: Session, user_id: uuid) -> UserGoal:
    goal = session.exec(select(UserGoal).where(UserGoal.created_for == user_id).where(UserGoal.active==True)).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return goal


def get_goals_for_user(session: Session, user_id: uuid.UUID) -> list[UserGoal]:
    goals = session.exec(
        select(UserGoal)
        .where(UserGoal.created_for == user_id)
        .order_by(UserGoal.created_at.desc())
    ).all()
    return list(goals)

def get_goals_created_consultant(session:Session, consultant_user_id:uuid,user_id:uuid)->list[UserGoal]:
    goals= session.exec(select(UserGoal).where(UserGoal.created_by==consultant_user_id).where(UserGoal.created_for == user_id)).all()
    if not goals:
        raise HTTPException(status_code=404, detail="Goals not found")
    return goals   

def create_goal_for_user(session: Session, user_id: uuid.UUID, payload: UserGoal, appointment_id: Optional[uuid.UUID] = None) -> UserGoal:
    g = UserGoal(
        created_for=user_id,
        created_by=payload.created_by if payload.created_by else user_id, # Should be set by caller usually
        appointment_id=appointment_id,
        goal_type=payload.goal_type,
        target_delta_kg=payload.target_delta_kg,
        duration_days=payload.duration_days,
        active=payload.active, # Consultant created might be inactive active? Let's respect payload
        start_date=payload.start_date,
        end_date=payload.end_date,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    
    if g.active:
        # Deactivate others
        existing_active = session.exec(select(UserGoal).where(UserGoal.created_for == user_id).where(UserGoal.active == True)).all()
        for ex in existing_active:
            ex.active = False
            session.add(ex)

    session.add(g)
    session.commit()
    session.refresh(g)
    return g


def upsert_goal_for_user(session: Session, user_id: uuid.UUID, payload: UserGoal) -> UserGoal:
    """Alias for create_goal_for_user since we treat upsert as creating a new version."""
    return create_goal_for_user(session, user_id, payload)


def delete_goal_for_user(session: Session, user_id: uuid.UUID) -> None:
    """Deactivate current goal."""
    goals = session.exec(select(UserGoal).where(UserGoal.created_for == user_id).where(UserGoal.active == True)).all()
    for g in goals:
        g.active = False
        session.add(g)
    session.commit()


def activate_goal_for_user(session: Session, user_id: uuid.UUID, goal_id: uuid.UUID) -> UserGoal:
    # 1. Verify ownership
    target_goal = session.get(UserGoal, goal_id)
    if not target_goal:
         raise HTTPException(status_code=404, detail="Goal not found")
    if target_goal.created_for != user_id:
         raise HTTPException(status_code=403, detail="Not your goal")
    
    # 2. Deactivate currently active goals
    existing = session.exec(select(UserGoal).where(UserGoal.created_for == user_id).where(UserGoal.active == True)).all()
    for ex in existing:
        ex.active = False
        session.add(ex)
    
    # 3. Activate target
    target_goal.active = True
    session.add(target_goal)
    session.commit()
    session.refresh(target_goal)
    return target_goal


