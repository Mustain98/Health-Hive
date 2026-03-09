from fastapi import HTTPException, status
from typing import Optional
from service import admin_service
from schemas.report import (
    ReportActionRequest,
    VerifyConsultantRequest,
    UserStatusRequest,
)


def dashboard_stats():
    return admin_service.get_stats()


def list_users(search: Optional[str] = None):
    return admin_service.get_all_users(search)


def update_user_status(admin_id: str, user_id: str, body: UserStatusRequest):
    if body.status not in {"active", "banned"}:
        raise HTTPException(status_code=400, detail="status must be 'active' or 'banned'")
    return admin_service.set_user_status(admin_id, user_id, body.status, body.note)


def list_consultants(filter_status: Optional[str] = None):
    return admin_service.get_consultants(filter_status)


def verify_consultant(admin_id: str, consultant_id: str, body: VerifyConsultantRequest):
    if body.decision not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="decision must be 'approve' or 'reject'")
    if body.decision == "reject" and not body.note:
        raise HTTPException(status_code=400, detail="note is required when rejecting")
    return admin_service.verify_consultant(admin_id, consultant_id, body.decision, body.note)


def list_reports(filter_status: Optional[str] = None):
    return admin_service.get_reports(filter_status)


def handle_report_action(admin_id: str, report_id: str, body: ReportActionRequest):
    if body.action not in {"remove", "resolve", "ban", "dismiss"}:
        raise HTTPException(status_code=400, detail="invalid action")
    try:
        return admin_service.action_report(admin_id, report_id, body.action, body.note)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


def audit_log(limit: int = 50):
    return admin_service.get_audit_log(limit)