from __future__ import annotations

import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlmodel import Session

from app.core.database import get_session
from app.core.auth import get_current_user, require_user_type
from app.modules.user.models import User
from app.modules.user.schemas import UserType
from app.modules.consultant.schemas import ConsultantProfileCreate, ConsultantProfileUpdate, ConsultantPublicRead, ConsultantDocumentCreate, ConsultantDocumentReadWithUrl
from app.modules.consultant.models import ConsultantProfile, ConsultantDocument
from app.modules.consultant.controllers.consultant import (
    upsert_profile_me,
    update_profile_me,
    search_public,
    read_public_profile,
    read_my_profile,
    upload_document_me,
    list_profile_documents,
    submit_application_me,
    get_my_application_status,
    upload_application_document_me,
)
from app.modules.consultant.schemas import DocumentType
from app.modules.consultant.services.consultant import get_document_public_url

router = APIRouter(prefix="/consultants", tags=["Consultants"])


# ============================================================
# PUBLIC / unauthenticated endpoints (no {profile_id} param)
# ============================================================

@router.get("", response_model=list[ConsultantPublicRead])
def list_consultants(
    q: str | None = None,
    verified_only: bool = False,
    limit: int = 20,
    offset: int = 0,
    session: Session = Depends(get_session),
):
    return search_public(session, query=q, verified_only=verified_only, limit=limit, offset=offset)


# ============================================================
# /apply/* routes
# ============================================================

@router.get("/apply/status", response_model=dict)
def check_my_application_status(
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """Check the status of the current user's consultant application."""
    return get_my_application_status(session, me)


@router.post("/apply", response_model=dict)
def submit_application(
    payload: ConsultantProfileCreate,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """Submit a new consultant application."""
    app = submit_application_me(session, me, payload)
    return {"message": "Application submitted successfully", "application_id": app.id}


@router.post("/apply/documents", response_model=dict)
def upload_application_document(
    application_id: str = Form(...),
    doc_type: DocumentType = Form(...),
    issuer: str | None = Form(None),
    issue_date: str | None = Form(None),
    expires_at: str | None = Form(None),
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """Upload a document to an existing pending application."""
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
    doc = upload_application_document_me(session, me, application_id, meta, file)
    return {"message": "Document uploaded successfully", "document_id": doc.id}


# ============================================================
# /me/* routes MUST come before /{profile_id} routes so that
# FastAPI does not try to coerce the literal string "me" into
# a UUID and raise a 422 / 500 before CORS headers are set.
# ============================================================

@router.get("/me/profile", response_model=ConsultantProfile)
def get_my_profile(
    session: Session = Depends(get_session),
    me: User = Depends(require_user_type(UserType.consultant)),
):
    p = read_my_profile(session, me)
    if not p:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Consultant profile not found")
    return p


@router.put("/me/profile", response_model=ConsultantProfile)
def create_or_replace_my_profile(
    payload: ConsultantProfileCreate,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    # this endpoint can "promote" a user to consultant when they create a profile
    return upsert_profile_me(session, me, payload)


@router.patch("/me/profile", response_model=ConsultantProfile)
def patch_my_profile(
    payload: ConsultantProfileUpdate,
    session: Session = Depends(get_session),
    me: User = Depends(require_user_type(UserType.consultant)),
):
    return update_profile_me(session, me, payload)


@router.post("/me/documents", response_model=ConsultantDocument)
def upload_my_document(
    consultant_profile_id: UUID = Form(...),
    doc_type: DocumentType = Form(DocumentType.certificate),
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


# ============================================================
# /{profile_id} routes — kept LAST so "me" is never captured
# ============================================================

@router.get("/{profile_id}", response_model=ConsultantPublicRead)
def get_consultant_profile(
    profile_id: UUID,
    session: Session = Depends(get_session),
):
    c = read_public_profile(session, profile_id)
    if not c:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Consultant not found")
    return c


@router.get("/{profile_id}/documents", response_model=list[ConsultantDocumentReadWithUrl])
def list_consultant_documents(
    profile_id: UUID,
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