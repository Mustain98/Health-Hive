from __future__ import annotations

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models.user_goal import UserGoal
from app.models.nutrition_target import NutritionTarget
from app.schemas.user_goal import GoalUpsert
from app.schemas.nutrition_target import NutritionTargetUpdate
from app.service.user_goal_service import upsert_goal_for_user, get_goal_for_user
from app.service.nutrition_target_service import get_current_target, upsert_target_manual
from app.service.permission_service import assert_permission
from app.service.audit_service import log_health_change
from app.models.consultant_access import AuditAction, AuditResource


def consultant_read_goal(session: Session, consultant_user_id: int, user_id: int) -> UserGoal:
    assert_permission(session, user_id=user_id, consultant_user_id=consultant_user_id, resource="user_goals", write=False)
    return get_goal_for_user(session, user_id)


def consultant_upsert_goal(session: Session, consultant_user_id: int, user_id: int, payload: GoalUpsert, appointment_id: int | None = None) -> UserGoal:
    assert_permission(session, user_id=user_id, consultant_user_id=consultant_user_id, resource="user_goals", write=True)

    before_obj = session.exec(select(UserGoal).where(UserGoal.user_id == user_id)).first()
    before = before_obj.model_dump() if before_obj else None

    goal = upsert_goal_for_user(session, user_id, payload)

    after = goal.model_dump()
    log_health_change(
        session,
        user_id=user_id,
        changed_by_user_id=consultant_user_id,
        resource=AuditResource.user_goals,
        action=AuditAction.update if before_obj else AuditAction.create,
        before=before,
        after=after,
        appointment_id=appointment_id,
    )
    return goal


def consultant_read_target(session: Session, consultant_user_id: int, user_id: int) -> NutritionTarget:
    assert_permission(session, user_id=user_id, consultant_user_id=consultant_user_id, resource="nutrition_targets", write=False)
    t = get_current_target(session, user_id)
    if not t:
        raise HTTPException(status_code=404, detail="Nutrition target not found")
    return t


def consultant_upsert_target(session: Session, consultant_user_id: int, user_id: int, payload: NutritionTargetUpdate, appointment_id: int | None = None) -> NutritionTarget:
    assert_permission(session, user_id=user_id, consultant_user_id=consultant_user_id, resource="nutrition_targets", write=True)

    before_obj = get_current_target(session, user_id)
    before = before_obj.model_dump() if before_obj else None

    t = upsert_target_manual(session, user_id, payload)

    after = t.model_dump()
    log_health_change(
        session,
        user_id=user_id,
        changed_by_user_id=consultant_user_id,
        resource=AuditResource.nutrition_targets,
        action=AuditAction.update if before_obj else AuditAction.create,
        before=before,
        after=after,
        appointment_id=appointment_id,
    )
    return t
