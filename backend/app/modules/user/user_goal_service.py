from datetime import datetime, timezone

from fastapi import HTTPException
from sqlmodel import Session, select
import uuid
from typing import Optional

from app.modules.user.models import UserGoal
from app.modules.user.models import UserGoalLog, UserGoalLogCreate, UserData
from app.modules.user.schemas import goal_type_for_milestone, validate_milestone_attributes
from app.modules.user.risk import assert_safe_milestone
from datetime import datetime, timezone, date, timedelta



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
    # milestone_type is authoritative when present: keep goal_type consistent for the macro pipeline.
    derived = goal_type_for_milestone(payload.milestone_type)
    g = UserGoal(
        created_for=user_id,
        created_by=payload.created_by if payload.created_by else user_id,
        appointment_id=appointment_id,
        goal_type=derived or payload.goal_type,
        milestone_type=payload.milestone_type,
        name=payload.name,
        target_weight=payload.target_weight,
        target_value=payload.target_value,
        unit=payload.unit,
        duration_days=payload.duration_days,
        active=payload.active,
        start_date=payload.start_date,
        end_date=payload.end_date,
        attributes=validate_milestone_attributes(payload.milestone_type, payload.attributes),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    if g.active:
        # Creating an *active* goal = activating it → must be safe (decision 3).
        assert_safe_milestone(session, user_id, g)
        # Deactivate others
        existing_active = session.exec(select(UserGoal).where(UserGoal.created_for == user_id).where(UserGoal.active == True)).all()
        for ex in existing_active:
            ex.active = False
            ex.start_date=None
            ex.end_date=None
            session.add(ex)
        session.flush()  # deactivate before inserting the new active row (partial unique index)

    session.add(g)
    session.commit()
    session.refresh(g)
    return g


def delete_goal_for_user(session: Session, user_id: uuid.UUID) -> None:
    """Deactivate current goal."""
    goals = session.exec(select(UserGoal).where(UserGoal.created_for == user_id).where(UserGoal.active == True)).all()
    for g in goals:
        g.active = False
        g.start_date=None
        g.end_date=None
        session.add(g)
    session.commit()


def delete_goal_by_id(session: Session, user_id: uuid.UUID, goal_id: uuid.UUID) -> None:
    """Permanently delete a specific milestone + its progress logs."""
    from sqlmodel import delete as _delete
    g = session.get(UserGoal, goal_id)
    if not g or g.created_for != user_id:
        raise HTTPException(status_code=404, detail="Goal not found")
    session.exec(_delete(UserGoalLog).where(UserGoalLog.goal_id == goal_id))  # cascade
    session.delete(g)
    session.commit()


def activate_goal_for_user(session: Session, user_id: uuid.UUID, goal_id: uuid.UUID) -> UserGoal:
    # 1. Verify ownership
    target_goal = session.get(UserGoal, goal_id)
    if not target_goal:
         raise HTTPException(status_code=404, detail="Goal not found")
    if target_goal.created_for != user_id:
         raise HTTPException(status_code=403, detail="Not your goal")

    # 1b. No entry point may activate an unsafe goal (decision 3). Checked before
    #     any mutation; is_risky falls back to the user's current weight.
    assert_safe_milestone(session, user_id, target_goal)

    # 2. Deactivate currently active goals
    existing = session.exec(select(UserGoal).where(UserGoal.created_for == user_id).where(UserGoal.active == True)).all()
    for ex in existing:
        ex.active = False
        session.add(ex)
    session.flush()  # deactivate before activating target (partial unique index)

    # 3. Activate target
    target_goal.active = True

    # 4. Set start/end dates. duration_days may be None for open-ended milestones
    #    (e.g. "maintain over time") — leave end_date unset in that case.
    start_date = date.today()
    target_goal.start_date = start_date
    target_goal.end_date = (
        start_date + timedelta(days=target_goal.duration_days)
        if target_goal.duration_days else None
    )
    target_goal.updated_at = datetime.now(timezone.utc)

    # 5. Read user's current weight from UserData as initial_weight
    user_data = session.exec(select(UserData).where(UserData.user_id == user_id)).first()
    if user_data and user_data.weight_kg:
        target_goal.initial_weight = user_data.weight_kg
        # Create an initial log at activation time
        initial_log = UserGoalLog(
            user_id=user_id,
            goal_id=target_goal.id,
            date=datetime.now(timezone.utc),
            weight=user_data.weight_kg,
            due_terget=0.0,  # Day-0, no progress required yet
        )
        session.add(initial_log)

    session.add(target_goal)
    session.commit()
    session.refresh(target_goal)
    return target_goal

def change_goal_date(
    session: Session,
    user_id: uuid.UUID,
    goal_id: uuid.UUID,
    new_start_date: date
) -> UserGoal:
    target_goal = session.get(UserGoal, goal_id)
    if not target_goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    if target_goal.created_for != user_id:
        raise HTTPException(status_code=403, detail="Not your goal")

    target_goal.start_date = new_start_date
    target_goal.end_date = (
        new_start_date + timedelta(days=target_goal.duration_days)
        if target_goal.duration_days else None
    )
    target_goal.updated_at = datetime.now(timezone.utc)

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

    # Calculate due target based on absolute target_weight and initial_weight
    if goal.start_date and goal.target_weight and goal.initial_weight and goal.duration_days:
        start_dt = datetime.combine(goal.start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        days_passed = (log_date - start_dt).days

        if days_passed < 0:
            days_passed = 0
        elif days_passed > goal.duration_days:
            days_passed = goal.duration_days

        # Total delta = target_weight - initial_weight (negative if losing)
        total_delta = goal.target_weight - goal.initial_weight
        daily_delta = total_delta / goal.duration_days
        due_target = daily_delta * days_passed  # Can be negative for weight loss

    new_log = UserGoalLog(
        user_id=user_id,
        goal_id=goal.id,
        date=log_date,
        weight=payload.weight,
        due_terget=due_target
    )
    session.add(new_log)

    # Also update the user's latest weight in UserData
    user_data = session.exec(select(UserData).where(UserData.user_id == user_id)).first()
    if user_data:
        user_data.weight_kg = payload.weight
        user_data.updated_at = datetime.now(timezone.utc)
        session.add(user_data)

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
