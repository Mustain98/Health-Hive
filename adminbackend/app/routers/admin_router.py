from fastapi import APIRouter, Depends, Query
from typing import Optional
from core.auth import get_current_user
from controller import admin_controller
from schemas.report import (
    ReportActionRequest,
    VerifyConsultantRequest,
    UserStatusRequest,
)

router = APIRouter(prefix="/api/admin", tags=["Admin"])


def require_admin(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.get("/stats")
def get_stats(admin=Depends(require_admin)):
    return admin_controller.dashboard_stats()


@router.get("/users")
def list_users(
    search: Optional[str] = Query(default=None),
    admin=Depends(require_admin),
):
    return admin_controller.list_users(search)


@router.patch("/users/{user_id}/status")
def update_user_status(
    user_id: str,
    body: UserStatusRequest,
    admin=Depends(require_admin),
):
    return admin_controller.update_user_status(admin["id"], user_id, body)


@router.get("/consultants")
def list_consultants(
    status: Optional[str] = Query(default=None),
    admin=Depends(require_admin),
):
    return admin_controller.list_consultants(status)


@router.patch("/consultants/{consultant_id}/verify")
def verify_consultant(
    consultant_id: str,
    body: VerifyConsultantRequest,
    admin=Depends(require_admin),
):
    return admin_controller.verify_consultant(admin["id"], consultant_id, body)


@router.get("/reports")
def list_reports(
    status: Optional[str] = Query(default=None),
    admin=Depends(require_admin),
):
    return admin_controller.list_reports(status)


@router.patch("/reports/{report_id}/action")
def action_report(
    report_id: str,
    body: ReportActionRequest,
    admin=Depends(require_admin),
):
    return admin_controller.handle_report_action(admin["id"], report_id, body)


@router.get("/audit-log")
def audit_log(
    limit: int = Query(default=50, le=200),
    admin=Depends(require_admin),
):
    return admin_controller.audit_log(limit)