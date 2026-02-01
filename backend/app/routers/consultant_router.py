from __future__ import annotations

from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlmodel import Session

from app.core.database import get_session
from app.core.auth import get_current_user, require_user_type
from app.models.user import User, UserType
from app.schemas.consultant import (
    ConsultantProfileCreate,
    ConsultantProfileUpdate,
    ConsultantProfileRead,
    ConsultantPublicRead,
    ConsultantDocumentRead,
    ConsultantDocumentCreate,
    ConsultantDocumentReadWithUrl,
    AvailabilityRuleCreate,
    AvailabilityRuleRead,
    AvailabilityRuleUpdate
)
from app.schemas.appointments import FreeWindowResponse
from app.controller.consultant_controller import (
    upsert_profile_me,
    update_profile_me,
    search_public,
    read_public_profile,
    read_my_profile,
    upload_document_me,
    list_profile_documents,

)
from app.models.consultant import DocumentType 
from app.service.consultant_service import get_document_public_url

router = APIRouter(prefix="/consultants", tags=["Consultants"])


@router.get("", response_model=list[ConsultantPublicRead])
def list_consultants(
    q: str | None = None,
    verified_only: bool = False,
    limit: int = 20,
    offset: int = 0,
    session: Session = Depends(get_session),
):
    return search_public(session, query=q, verified_only=verified_only, limit=limit, offset=offset)


@router.get("/{profile_id}", response_model=ConsultantPublicRead)
def get_consultant_profile(
    profile_id: int,
    session: Session = Depends(get_session),
):
    c = read_public_profile(session, profile_id)
    if not c:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Consultant not found")
    return c


@router.get("/{profile_id}/documents", response_model=list[ConsultantDocumentReadWithUrl])
def list_consultant_documents(
    profile_id: int,
    session: Session = Depends(get_session),
):
    docs = list_profile_documents(session, profile_id)

    return [
        ConsultantDocumentReadWithUrl(
            id=d.id,
            consultant_profile_id=d.consultant_profile_id,
            doc_type=d.doc_type,
            issuer=d.issuer,
            issue_date=d.issue_date,
            expires_at=d.expires_at,
            bucket=d.bucket,
            file_path=d.file_path,
            is_verified=d.is_verified,
            verification_note=d.verification_note,
            created_at=d.created_at,
            file_url=get_document_public_url(d),
        )
        for d in docs
    ]


@router.get("/{profile_id}/free-windows", response_model=list[FreeWindowResponse])
def get_consultant_free_windows(
    profile_id: int,
    date: str,  # YYYY-MM-DD format
    session: Session = Depends(get_session),
):
    from datetime import date as date_type
    from app.service.user_side_appointment_service import get_free_windows_for_date
    from app.models.consultant import ConsultantProfile
    from fastapi import HTTPException
    
    # Resolve profile ID to user ID
    profile = session.get(ConsultantProfile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Consultant profile not found")
    
    target_date = date_type.fromisoformat(date)
    windows = get_free_windows_for_date(
        session, consultant_user_id=profile.user_id, target_date=target_date
    )
    
    return [
        FreeWindowResponse(start=start, end=end)
        for start, end in windows
    ]




# ---------- consultant self management ----------

@router.get("/me/profile", response_model=ConsultantProfileRead)
def get_my_profile(
    session: Session = Depends(get_session),
    me: User = Depends(require_user_type(UserType.consultant)),
):
    p = read_my_profile(session, me)
    # if they are consultant but no profile yet, you can return 404
    if not p:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Consultant profile not found")
    return p


@router.put("/me/profile", response_model=ConsultantProfileRead)
def create_or_replace_my_profile(
    payload: ConsultantProfileCreate,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    # this endpoint can "promote" a user to consultant when they create a profile
    return upsert_profile_me(session, me, payload)


@router.patch("/me/profile", response_model=ConsultantProfileRead)
def patch_my_profile(
    payload: ConsultantProfileUpdate,
    session: Session = Depends(get_session),
    me: User = Depends(require_user_type(UserType.consultant)),
):
    return update_profile_me(session, me, payload)


@router.post("/me/documents", response_model=ConsultantDocumentRead)
def upload_my_document(
    consultant_profile_id: int = Form(...),
    doc_type: DocumentType = Form(DocumentType.CERTIFICATE),
    issuer: str | None = Form(None),
    issue_date: str | None = Form(None),
    expires_at: str | None = Form(None),
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    me: User = Depends(require_user_type(UserType.consultant)),
):
    from datetime import date

    def _parse(d: str | None):
        if not d:
            return None
        return date.fromisoformat(d)

    meta = ConsultantDocumentCreate(
        doc_type=doc_type,
        issuer=issuer,
        issue_date=_parse(issue_date),
        expires_at=_parse(expires_at),
    )
    return upload_document_me(session, me, consultant_profile_id, meta, file)


# ---------- availability rules ----------

@router.get("/me/availability", response_model=list)
def get_my_availability_rules(
    session: Session = Depends(get_session),
    me: User = Depends(require_user_type(UserType.consultant)),
):
    from app.controller.consultant_controller import list_my_availability_rules
    return list_my_availability_rules(session, me)


@router.post("/me/availability")
def create_my_availability_rule(
    rule_data: AvailabilityRuleCreate,
    session: Session = Depends(get_session),
    me: User = Depends(require_user_type(UserType.consultant)),
):
    from app.controller.consultant_controller import create_availability_rule
    return create_availability_rule(session, me, rule_data)


@router.patch("/me/availability/{rule_id}")
def update_my_availability_rule(
    rule_id: int,
    updates: AvailabilityRuleUpdate,
    session: Session = Depends(get_session),
    me: User = Depends(require_user_type(UserType.consultant)),
):
    from app.controller.consultant_controller import update_availability_rule
    return update_availability_rule(session, me, rule_id, updates)


@router.delete("/me/availability/{rule_id}", status_code=204)
def delete_my_availability_rule(
    rule_id: int,
    session: Session = Depends(get_session),
    me: User = Depends(require_user_type(UserType.consultant)),
):
    from app.controller.consultant_controller import delete_availability_rule
    delete_availability_rule(session, me, rule_id)