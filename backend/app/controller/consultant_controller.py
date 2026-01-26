from __future__ import annotations

from fastapi import UploadFile
from sqlmodel import Session

from app.models.user import User
from app.models.consultant import ConsultantProfile, ConsultantDocument
from app.schemas.consultant import ConsultantProfileCreate, ConsultantProfileUpdate, ConsultantDocumentCreate
from app.service.consultant_service import (
    upsert_my_profile,
    update_my_profile,
    search_consultants,
    get_profile_public,
    get_profile_by_user_id,
    add_document_supabase,
    list_documents,
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
