from fastapi import APIRouter, Depends, Query, UploadFile, File
from typing import Optional, List
from core.auth import get_current_user
from controller import admin_controller
from schemas.report import VerifyConsultantRequest

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


@router.get("/consultations")
def consultations_summary(admin=Depends(require_admin)):
    """Booking-funnel overview — aggregate counts only, no consultation content."""
    return admin_controller.consultations_summary()


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


@router.get("/consultants/{consultant_id}/documents")
def get_consultant_documents(
    consultant_id: str,
    admin=Depends(require_admin),
):
    return admin_controller.get_consultant_documents(consultant_id)


# ── Applications ──────────────────────────────────────────────────────────────

@router.get("/applications")
def list_applications(
    status: Optional[str] = Query(default=None),
    admin=Depends(require_admin),
):
    return admin_controller.list_applications(status)


@router.post("/applications/{app_id}/review")
def review_application(
    app_id: str,
    body: VerifyConsultantRequest,
    admin=Depends(require_admin),
):
    """
    body.decision should be 'approve' or 'reject'
    body.note is optional but required for rejection
    """
    return admin_controller.review_application(admin["id"], app_id, body)


@router.post("/consultants/{consultant_id}/documents/{doc_id}/review")
def review_consultant_document(
    consultant_id: str,
    doc_id: str,
    body: VerifyConsultantRequest,
    admin=Depends(require_admin),
):
    """Verify or reject (delete) a specific consultant document."""
    return admin_controller.review_consultant_document(admin["id"], consultant_id, doc_id, body)


# ── Food Items ────────────────────────────────────────────────────────────────

@router.get("/food-items")
def list_food_items(
    search: Optional[str] = Query(default=None),
    label: Optional[str] = Query(default=None),
    admin=Depends(require_admin),
):
    return admin_controller.list_food_items(search, label)


@router.get("/food-labels")
def list_food_labels(admin=Depends(require_admin)):
    return admin_controller.list_food_labels()


@router.post("/food-items")
def create_food_item(
    body: dict,
    admin=Depends(require_admin),
):
    return admin_controller.create_food_item(body)


@router.delete("/food-items/{item_id}")
def delete_food_item(
    item_id: str,
    admin=Depends(require_admin),
):
    return admin_controller.delete_food_item(item_id)


# ── AI Food Item Generation ───────────────────────────────────────────────────

@router.post("/food-items/generate")
def generate_food_item(
    body: dict,
    admin=Depends(require_admin),
):
    query = body.get("query", "").strip()
    if not query:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="query is required")
    return admin_controller.generate_food_item_via_ai(query)


# ── Meals ─────────────────────────────────────────────────────────────────────

@router.get("/meals")
def list_meals(
    search: Optional[str] = Query(default=None),
    label: Optional[List[str]] = Query(default=None),
    admin=Depends(require_admin),
):
    return admin_controller.list_meals(search, label)


@router.get("/meal-labels")
def list_meal_labels(admin=Depends(require_admin)):
    return admin_controller.list_meal_labels()


@router.post("/meals")
def create_meal(
    body: dict,
    admin=Depends(require_admin),
):
    return admin_controller.create_meal(body)


@router.patch("/meals/{meal_id}")
def update_meal(
    meal_id: str,
    body: dict,
    admin=Depends(require_admin),
):
    return admin_controller.update_meal(meal_id, body)

@router.post("/meals/{meal_id}/upload-image")
async def upload_meal_image(
    meal_id: str,
    file: UploadFile = File(...),
    admin=Depends(require_admin),
):
    return await admin_controller.upload_meal_image(meal_id, file)


@router.delete("/meals/{meal_id}")
def delete_meal(
    meal_id: str,
    admin=Depends(require_admin),
):
    return admin_controller.delete_meal(meal_id)

