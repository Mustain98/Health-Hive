from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models.consultant_access import (
    ConsultantPermission,
    PermissionScope,
    PermissionStatus,
)
from app.models.user import User, UserType


def _utc_now():
    return datetime.now(timezone.utc)


def _ensure_consultant(session: Session, consultant_user_id: int) -> User:
    u = session.get(User, consultant_user_id)
    if not u:
        raise HTTPException(status_code=404, detail="Consultant not found")
    if u.user_type != UserType.consultant:
        raise HTTPException(status_code=400, detail="Target user is not a consultant")
    return u


def grant_permission(
    session: Session,
    user_id: int,
    consultant_user_id: int,
    scope: PermissionScope,
    resources: list[str],
    granted_in_appointment_id: Optional[int] = None,
) -> ConsultantPermission:
    _ensure_consultant(session, consultant_user_id)

    # one active record per pair (update-in-place)
    existing = session.exec(
        select(ConsultantPermission).where(
            ConsultantPermission.user_id == user_id,
            ConsultantPermission.consultant_user_id == consultant_user_id,
        )
    ).first()

    now = _utc_now()
    if existing:
        existing.scope = scope
        existing.resources = resources
        existing.status = PermissionStatus.active
        existing.granted_at = now
        existing.revoked_at = None
        existing.granted_in_appointment_id = granted_in_appointment_id
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing

    p = ConsultantPermission(
        user_id=user_id,
        consultant_user_id=consultant_user_id,
        scope=scope,
        resources=resources,
        status=PermissionStatus.active,
        granted_at=now,
        granted_in_appointment_id=granted_in_appointment_id,
        created_at=now,
    )
    session.add(p)
    session.commit()
    session.refresh(p)
    return p


def revoke_permission(session: Session, user_id: int, consultant_user_id: int) -> None:
    existing = session.exec(
        select(ConsultantPermission).where(
            ConsultantPermission.user_id == user_id,
            ConsultantPermission.consultant_user_id == consultant_user_id,
            ConsultantPermission.status == PermissionStatus.active,
        )
    ).first()
    if not existing:
        return

    existing.status = PermissionStatus.revoked
    existing.revoked_at = _utc_now()
    session.add(existing)
    session.commit()


def list_permissions_for_user(session: Session, user_id: int) -> list[ConsultantPermission]:
    return list(
        session.exec(
            select(ConsultantPermission).where(ConsultantPermission.user_id == user_id)
        ).all()
    )


def assert_permission(
    session: Session,
    user_id: int,
    consultant_user_id: int,
    resource: str,
    write: bool,
) -> ConsultantPermission:
    p = session.exec(
        select(ConsultantPermission).where(
            ConsultantPermission.user_id == user_id,
            ConsultantPermission.consultant_user_id == consultant_user_id,
            ConsultantPermission.status == PermissionStatus.active,
        )
    ).first()

    if not p:
        raise HTTPException(status_code=403, detail="No active permission for this user/consultant")

    if resource not in (p.resources or []):
        raise HTTPException(status_code=403, detail=f"Permission does not include resource: {resource}")

    if write and p.scope != PermissionScope.read_write:
        raise HTTPException(status_code=403, detail="Write permission required")

    return p
