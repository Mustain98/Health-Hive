from __future__ import annotations

from fastapi import UploadFile
from sqlmodel import Session

from app.modules.user.models import User
from app.modules.consultant.models import ConsultantProfile, ConsultantDocument
from app.modules.consultant.models import ConsultantProfileCreate, ConsultantProfileUpdate, ConsultantDocumentCreate
from app.modules.consultant.consultant_service import (
    upsert_my_profile,
    update_my_profile,
    search_consultants,
    get_profile_public,
    get_profile_by_user_id,
    add_document_supabase,
    list_documents,
    submit_consultant_application,
    get_application_by_user_id,
    add_application_document_supabase,
)

def submit_application_me(session: Session, me: User, payload: ConsultantProfileCreate):
    return submit_consultant_application(
        session,
        me,
        display_name=payload.display_name,
        bio=payload.bio,
        specialties=payload.specialties,
        other_info=payload.other_info,
        consultant_type=payload.consultant_type,
        highest_qualification=payload.highest_qualification,
        graduation_institution=payload.graduation_institution,
        registration_body=payload.registration_body,
        registration_number=payload.registration_number,
    )

def get_my_application_status(session: Session, me: User):
    app = get_application_by_user_id(session, me.id)
    if not app:
        return {"status": "none"}
    
    return {
        "id": app.id,
        "status": app.status,
        "admin_note": app.admin_note,
        "submitted_at": app.created_at
    }

def upload_application_document_me(
    session: Session,
    me: User,
    application_id: str,
    meta: ConsultantDocumentCreate,
    file: UploadFile,
):
    return add_application_document_supabase(
        session,
        me,
        application_id,
        doc_type=meta.doc_type,
        issuer=meta.issuer,
        issue_date=meta.issue_date,
        expires_at=meta.expires_at,
        file=file,
    )


def upsert_profile_me(session: Session, me: User, payload: ConsultantProfileCreate) -> ConsultantProfile:
    return upsert_my_profile(
        session,
        me,
        display_name=payload.display_name,
        bio=payload.bio,
        specialties=payload.specialties,
        other_info=payload.other_info,
        consultant_type=payload.consultant_type,
        highest_qualification=payload.highest_qualification,
        graduation_institution=payload.graduation_institution,
        registration_body=payload.registration_body,
        registration_number=payload.registration_number,
    )


def update_profile_me(session: Session, me: User, payload: ConsultantProfileUpdate) -> ConsultantProfile:
    return update_my_profile(
        session,
        me,
        display_name=payload.display_name,
        bio=payload.bio,
        specialties=payload.specialties,
        other_info=payload.other_info,
        consultant_type=payload.consultant_type,
        highest_qualification=payload.highest_qualification,
        graduation_institution=payload.graduation_institution,
        registration_body=payload.registration_body,
        registration_number=payload.registration_number,
    )


def search_public(session: Session, query: str | None, verified_only: bool, limit: int, offset: int) -> list[ConsultantProfile]:
    return search_consultants(session, query=query, verified_only=verified_only, limit=limit, offset=offset)


def read_public_profile(session: Session, profile_id: int) -> ConsultantProfile:
    return get_profile_public(session, profile_id)


def read_my_profile(session: Session, me: User) -> ConsultantProfile | None:
    return get_profile_by_user_id(session, me.id)


def upload_document_me(
    session: Session,
    me: User,
    profile_id: int,
    meta: ConsultantDocumentCreate,
    file: UploadFile,
) -> ConsultantDocument:
    return add_document_supabase(
        session,
        me,
        profile_id,
        doc_type=meta.doc_type,
        issuer=meta.issuer,
        issue_date=meta.issue_date,
        expires_at=meta.expires_at,
        file=file,
    )


def list_profile_documents(session: Session, profile_id: int) -> list[ConsultantDocument]:
    return list_documents(session, profile_id)
