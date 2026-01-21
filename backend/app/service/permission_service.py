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

    # Fetch ALL existing records for this pair to avoid duplicates
    existing_records = session.exec(
        select(ConsultantPermission).where(
            ConsultantPermission.user_id == user_id,
            ConsultantPermission.consultant_user_id == consultant_user_id,
        )
    ).all()

    now = _utc_now()
    active_record = None

    # If we have records, reuse the first one and ensure others are revoked/cleaned if possible
    # For simplicity in this fix, we'll pick the first one to be the ACTIVE one, and ensure others are not active?
    # Or just reuse one and ignore others?
    # Better: Pick the most recently updated or created one?
    # safely: Pick the first one found.

    if existing_records:
        active_record = existing_records[0]
        # If there are duplicates, we should strictly only have one active.
        # But grant_permission is about *enabling* access.
        # So we take the first one, update it to active, and if we were paranoid we'd revoke others.
        # Let's just update the first one. `revoke_permission` will handle cleaning up multiple actives if they exist.
        
        active_record.scope = scope
        active_record.resources = resources
        active_record.status = PermissionStatus.active
        active_record.granted_at = now
        active_record.revoked_at = None
        active_record.granted_in_appointment_id = granted_in_appointment_id
        
        session.add(active_record)
        
        # If there are others, we should probably ensure they are NOT active to enforce uniqueness?
        # This fixes the "grant creates duplicate if first found was revoked but another active exists" issue
        for other in existing_records[1:]:
             if other.status == PermissionStatus.active:
                 other.status = PermissionStatus.revoked
                 other.revoked_at = now
                 session.add(other)

        session.commit()
        session.refresh(active_record)
        return active_record

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
    # Revoke ALL active permissions for this pair
    active_perms = session.exec(
        select(ConsultantPermission).where(
            ConsultantPermission.user_id == user_id,
            ConsultantPermission.consultant_user_id == consultant_user_id,
            ConsultantPermission.status == PermissionStatus.active,
        )
    ).all()

    if not active_perms:
        return

    now = _utc_now()
    for p in active_perms:
        p.status = PermissionStatus.revoked
        p.revoked_at = now
        session.add(p)
    
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
