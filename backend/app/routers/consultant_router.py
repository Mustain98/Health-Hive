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
)
from app.controller.consultant_controller import (
    upsert_profile_me,
    update_profile_me,
    search_public,
    read_public_profile,
    read_my_profile,
    upload_document_me,
    list_profile_documents,
)

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
    return read_public_profile(session, profile_id)


@router.get("/{profile_id}/documents", response_model=list[ConsultantDocumentRead])
def list_consultant_documents(
    profile_id: int,
    session: Session = Depends(get_session),
):
    return list_profile_documents(session, profile_id)


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
    doc_type: str = Form("certificate"),
    title: str = Form(...),
    issuer: str | None = Form(None),
    issue_date: str | None = Form(None),   # YYYY-MM-DD
    expires_at: str | None = Form(None),   # YYYY-MM-DD
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    me: User = Depends(require_user_type(UserType.consultant)),
):
    # parse dates safely
    from datetime import date
    def _parse(d: str | None):
        if not d:
            return None
        return date.fromisoformat(d)

    meta = ConsultantDocumentCreate(
        doc_type=doc_type,
        title=title,
        issuer=issuer,
        issue_date=_parse(issue_date),
        expires_at=_parse(expires_at),
    )
    return upload_document_me(session, me, consultant_profile_id, meta, file)
