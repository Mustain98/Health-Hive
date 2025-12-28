from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.database import get_session
from app.core.auth import get_current_user
from app.models.user import User
from app.schemas.permission import PermissionGrant, PermissionRead, PermissionRevoke
from app.controller.permission_controller import grant_me, revoke_me, list_me

router = APIRouter(prefix="/permissions", tags=["Permissions"])


@router.get("/me", response_model=list[PermissionRead])
def list_my_permissions(
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    return list_me(session, me.id)


@router.post("/me/grant", response_model=PermissionRead)
def grant_permission_to_consultant(
    payload: PermissionGrant,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    return grant_me(session, me.id, payload)


@router.post("/me/revoke")
def revoke_permission_to_consultant(
    payload: PermissionRevoke,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    revoke_me(session, me.id, payload.consultant_user_id)
    return {"ok": True}
