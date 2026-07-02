from __future__ import annotations

import uuid
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.database import get_session
from app.core.auth import require_user_type
from app.modules.user.models import User, UserType
from app.modules.user.models import UserGoal
# I will define a placeholder GoalUpsert if it's strictly required for the function signature to be valid python, 
# but for now I will assume the user will fix the model later or it is imported from somewhere else in reality.
# Actually I should verify if GoalUpsert exists in user_goal.py. I read user_goal.py and it was NOT there.
# So I will comment it out or replace it with dict/Any for now to make it runnable?
# "get to the permission part later for now convert all the int to uuid"
# I'll update the IDs and leave the broken import issues for the "missing models" step if I haven't fixed it yet.
# However, if I write this file back with `GoalUpsert` in the import, it might crash if I don't fix it. 
# But I am only asked to convert int to uuid.
# I'll stick to the plan: Convert IDs. 
# I will try to keep the import for GoalUpsert but if it fails I'll know.
# Actually, I'll check if I can interpret `GoalUpsert` from context. It's likely `UserGoalUpdate` or similar.
# `UserGoal` has `UserGoalUpdate`. I'll use `UserGoalUpdate` or just keep `GoalUpsert` and let it break if it must. 
# But the user said "convert all the int to uuid". 
# I will just change int to UUID.

from app.modules.user.models import NutritionTarget, NutritionTargetUpdate
from app.modules.consultant.consultant_manage_user_controller import (
    read_user_goal,
    create_user_goal,
    read_user_target,
    create_user_target,
    read_user_meal_plan_setting,
    create_user_meal_plan_setting,
)

router = APIRouter(prefix="/consultant", tags=["Consultant Actions"])


@router.get("/users/{user_id}/goal", response_model=UserGoal)
def consultant_get_user_goal(
    user_id: UUID,
    session: Session = Depends(get_session),
    me: User = Depends(require_user_type(UserType.consultant)),
):
    return read_user_goal(session, me.id, user_id)


@router.post("/users/{user_id}/goal", response_model=UserGoal)
def consultant_post_user_goal(
    user_id: UUID,
    payload: UserGoal, 
    appointment_id: UUID | None = None,
    session: Session = Depends(get_session),
    me: User = Depends(require_user_type(UserType.consultant)),
):
    return create_user_goal(session, me.id, user_id, payload, appointment_id=appointment_id)


@router.get("/users/{user_id}/nutrition-target", response_model=NutritionTarget)
def consultant_get_user_target(
    user_id: UUID,
    session: Session = Depends(get_session),
    me: User = Depends(require_user_type(UserType.consultant)),
):
    return read_user_target(session, me.id, user_id)


@router.post("/users/{user_id}/nutrition-target", response_model=NutritionTarget)
def consultant_post_user_target(
    user_id: UUID,
    payload: NutritionTargetUpdate,
    appointment_id: UUID | None = None,
    session: Session = Depends(get_session),
    me: User = Depends(require_user_type(UserType.consultant)),
):
    return create_user_target(session, me.id, user_id, payload, appointment_id=appointment_id)


@router.get("/users/{user_id}/meal-plan-setting")
def consultant_get_user_meal_plan_setting(
    user_id: UUID,
    session: Session = Depends(get_session),
    me: User = Depends(require_user_type(UserType.consultant)),
):
    return read_user_meal_plan_setting(session, me.id, user_id)


@router.post("/users/{user_id}/meal-plan-setting")
def consultant_post_user_meal_plan_setting(
    user_id: UUID,
    payload: dict,
    appointment_id: UUID | None = None,
    session: Session = Depends(get_session),
    me: User = Depends(require_user_type(UserType.consultant)),
):
    return create_user_meal_plan_setting(session, me.id, user_id, payload, appointment_id=appointment_id)
