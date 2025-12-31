from __future__ import annotations

from sqlmodel import Session

from app.models.consultant_access import ConsultantPermission
from app.schemas.permission import PermissionGrant
from app.service.permission_service import grant_permission, revoke_permission, list_permissions_for_user


def grant_me(session: Session, user_id: int, payload: PermissionGrant) -> ConsultantPermission:
    return grant_permission(
        session,
        user_id=user_id,
        consultant_user_id=payload.consultant_user_id,
        scope=payload.scope,
        resources=payload.resources,
        granted_in_appointment_id=payload.granted_in_appointment_id,
    )


def revoke_me(session: Session, user_id: int, consultant_user_id: int) -> None:
    return revoke_permission(session, user_id=user_id, consultant_user_id=consultant_user_id)


def list_me(session: Session, user_id: int) -> list[ConsultantPermission]:
    return list_permissions_for_user(session, user_id=user_id)
