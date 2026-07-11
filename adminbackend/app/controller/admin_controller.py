from fastapi import HTTPException, status, UploadFile
from typing import Optional, List
from service import admin_service
from schemas.report import VerifyConsultantRequest


def dashboard_stats():
    return admin_service.get_stats()


def list_users(search: Optional[str] = None):
    return admin_service.get_all_users(search)


def consultations_summary():
    return admin_service.get_consultations_summary()


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


def review_consultant_document(admin_id: str, consultant_id: str, doc_id: str, body: VerifyConsultantRequest):
    if body.decision not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="decision must be 'approve' or 'reject'")
    result = admin_service.review_consultant_document(consultant_id, doc_id, body.decision, body.note)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to review document"))
    return result


def list_applications(status: Optional[str] = None):
    return admin_service.get_applications(status)

def review_application(admin_id: str, app_id: str, body: VerifyConsultantRequest):
    if body.decision not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="decision must be 'approve' or 'reject'")
    if body.decision == "reject" and not body.note:
        raise HTTPException(status_code=400, detail="note is required when rejecting")
    
    dec = "approved" if body.decision == "approve" else "rejected"
    result = admin_service.review_application(app_id, admin_id, dec, body.note)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to review application"))
    return result


def list_food_items(search: Optional[str] = None, label: Optional[str] = None):
    return admin_service.get_food_items(search, label)

def list_food_labels():
    return admin_service.get_food_labels()


def create_food_item(body: dict):
    try:
        return admin_service.create_food_item(body)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def delete_food_item(item_id: str):
    try:
        return admin_service.delete_food_item(item_id)
    except HTTPException:
        raise
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

def list_meals(search: Optional[str] = None, label: Optional[List[str]] = None):
    return admin_service.get_meals(search, label)


def list_meal_labels():
    return admin_service.get_meal_labels()


def create_meal(body: dict):
    try:
        return admin_service.create_meal(body)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

def update_meal(meal_id: str, body: dict):
    try:
        return admin_service.update_meal(meal_id, body)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def delete_meal(meal_id: str):
    try:
        return admin_service.delete_meal(meal_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

async def upload_meal_image(meal_id: str, file: UploadFile):
    try:
        file_bytes = await file.read()
        return admin_service.upload_meal_image(meal_id, file_bytes, file.content_type, file.filename)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
