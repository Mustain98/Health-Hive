from datetime import datetime, timezone

from fastapi import HTTPException
from sqlmodel import Session, select
import uuid
from typing import Optional

from app.models.user_goal import UserGoal
from app.models.user_data import UserGoalLog, UserGoalLogCreate




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


def add_goal_log(session: Session, user_id: uuid.UUID, payload: UserGoalLogCreate) -> UserGoalLog:
    # Get active goal
    goal = session.exec(
        select(UserGoal)
        .where(UserGoal.created_for == user_id)
        .where(UserGoal.active == True)
    ).first()
    
    if not goal:
        raise HTTPException(status_code=400, detail="No active goal to log against")

    log_date = payload.date or datetime.now(timezone.utc)
    due_target = 0.0

    # Calculate due target if goal has the necessary fields
    if goal.start_date and goal.target_delta_kg and goal.duration_days:
        start_dt = datetime.combine(goal.start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        days_passed = (log_date - start_dt).days
        
        if days_passed < 0:
            days_passed = 0
        elif days_passed > goal.duration_days:
            days_passed = goal.duration_days
            
        daily_delta = goal.target_delta_kg / goal.duration_days
        due_target = daily_delta * days_passed
        # If lose, we might want to represent it as a negative progression depending on frontend,
        # but the model says due_target: float. We will just store the absolute progress expected.

    new_log = UserGoalLog(
        user_id=user_id,
        goal_id=goal.id,
        date=log_date,
        weight=payload.weight,
        due_terget=due_target
    )
    session.add(new_log)
    session.commit()
    session.refresh(new_log)
    return new_log


def get_goal_logs(session: Session, user_id: uuid.UUID, goal_id: uuid.UUID) -> list[UserGoalLog]:
    # Ensure goal is owned by user
    goal = session.get(UserGoal, goal_id)
    if not goal or goal.created_for != user_id:
        # Don't throw 403 here, just return empty so consultant views don't crash
        # Actually consultant will access this via a different method, so this is fine for user route
        raise HTTPException(status_code=403, detail="Not permitted to view this goal's logs")

    logs = session.exec(
        select(UserGoalLog)
        .where(UserGoalLog.goal_id == goal_id)
        .order_by(UserGoalLog.date.asc())
    ).all()
    return list(logs)
