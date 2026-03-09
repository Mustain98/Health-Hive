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


def get_consultant_documents(consultant_id: str):
    return admin_service.get_consultant_documents(consultant_id)


def list_food_items(search: Optional[str] = None, label: Optional[str] = None):
    return admin_service.get_food_items(search, label)

def list_food_labels():
    return admin_service.get_food_labels()


def create_food_item(body: dict):
    try:
        return admin_service.create_food_item(body)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def delete_food_item(item_id: str):
    try:
        return admin_service.delete_food_item(item_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── AI Food Item Generation ───────────────────────────────────────────────────

def generate_food_item_via_ai(query: str):
    try:
        from service import ai_service
        return ai_service.generate_food_item(query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI generation failed: {str(e)}")


# ── Meals ─────────────────────────────────────────────────────────────────────

def list_meals(search: Optional[str] = None, label: Optional[str] = None):
    return admin_service.get_meals(search, label)


def list_meal_labels():
    return admin_service.get_meal_labels()


def create_meal(body: dict):
    try:
        return admin_service.create_meal(body)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def delete_meal(meal_id: str):
    try:
        return admin_service.delete_meal(meal_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
