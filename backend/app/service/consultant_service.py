from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, UploadFile
from sqlmodel import Session, select

from app.core.supabase_client import get_supabase_client
from app.models.consultant import ConsultantProfile, ConsultantDocument, ConsultantType, DocumentType
from app.models.user import User


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def get_profile_by_user_id(session: Session, user_id: int) -> Optional[ConsultantProfile]:
    return session.exec(select(ConsultantProfile).where(ConsultantProfile.user_id == user_id)).first()


def upsert_my_profile(
    session: Session,
    me: User,
    *,
    display_name: str,
    bio: Optional[str],
    specialties: Optional[str],
    other_info: Optional[str],
    consultant_type: ConsultantType,
    highest_qualification: str,
    graduation_institution: Optional[str],
    registration_body: Optional[str],
    registration_number: Optional[str],
) -> ConsultantProfile:
    p = get_profile_by_user_id(session, me.id)
    now = _utc_now()

    if not p:
        p = ConsultantProfile(
            user_id=me.id,
            display_name=display_name,
            bio=bio,
            specialties=specialties,
            other_info=other_info,
            consultant_type=consultant_type,
            highest_qualification=highest_qualification,
            graduation_institution=graduation_institution,
            registration_body=registration_body,
            registration_number=registration_number,
            is_verified=False,
            verified_at=None,
            created_at=now,
            updated_at=now,
        )
        session.add(p)
        session.commit()
        session.refresh(p)
        return p

    p.display_name = display_name
    p.bio = bio
    p.specialties = specialties
    p.other_info = other_info

    p.consultant_type = consultant_type
    p.highest_qualification = highest_qualification
    p.graduation_institution = graduation_institution
    p.registration_body = registration_body
    p.registration_number = registration_number

    p.updated_at = now
    session.add(p)
    session.commit()
    session.refresh(p)
    return p


def update_my_profile(
    session: Session,
    me: User,
    *,
    display_name: Optional[str] = None,
    bio: Optional[str] = None,
    specialties: Optional[str] = None,
    other_info: Optional[str] = None,
    consultant_type: Optional[ConsultantType] = None,
    highest_qualification: Optional[str] = None,
    graduation_institution: Optional[str] = None,
    registration_body: Optional[str] = None,
    registration_number: Optional[str] = None,
) -> ConsultantProfile:
    p = get_profile_by_user_id(session, me.id)
    if not p:
        raise HTTPException(status_code=404, detail="Consultant profile not found. Create it first.")

    if display_name is not None:
        p.display_name = display_name
    if bio is not None:
        p.bio = bio
    if specialties is not None:
        p.specialties = specialties
    if other_info is not None:
        p.other_info = other_info

    if consultant_type is not None:
        p.consultant_type = consultant_type
    if highest_qualification is not None:
        p.highest_qualification = highest_qualification
    if graduation_institution is not None:
        p.graduation_institution = graduation_institution
    if registration_body is not None:
        p.registration_body = registration_body
    if registration_number is not None:
        p.registration_number = registration_number

    p.updated_at = _utc_now()
    session.add(p)
    session.commit()
    session.refresh(p)
    return p


def search_consultants(
    session: Session,
    query: Optional[str] = None,
    verified_only: bool = False,
    limit: int = 20,
    offset: int = 0,
) -> list[ConsultantProfile]:
    stmt = select(ConsultantProfile)
    if verified_only:
        stmt = stmt.where(ConsultantProfile.is_verified == True)  # noqa: E712
    if query:
        like = f"%{query.strip()}%"
        stmt = stmt.where(ConsultantProfile.display_name.ilike(like))

    stmt = stmt.order_by(ConsultantProfile.display_name).offset(offset).limit(limit)
    return list(session.exec(stmt).all())


def get_profile_public(session: Session, profile_id: int) -> ConsultantProfile:
    p = session.get(ConsultantProfile, profile_id)
    if not p:
        raise HTTPException(status_code=404, detail="Consultant profile not found")
    return p


def list_documents(session: Session, consultant_profile_id: int) -> list[ConsultantDocument]:
    return list(
        session.exec(
            select(ConsultantDocument)
            .where(ConsultantDocument.consultant_profile_id == consultant_profile_id)
            .order_by(ConsultantDocument.created_at.desc())
        ).all()
    )


def add_document_supabase(
    session: Session,
    me: User,
    consultant_profile_id: int,
    *,
    doc_type: DocumentType,
    issuer: Optional[str],
    issue_date,
    expires_at,
    file: UploadFile,
) -> ConsultantDocument:
    profile = session.get(ConsultantProfile, consultant_profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Consultant profile not found")
    if profile.user_id != me.id:
        raise HTTPException(status_code=403, detail="Not your profile")

    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    raw = file.file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")

    sha = hashlib.sha256(raw).hexdigest()

    supabase = get_supabase_client()
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured (missing URL/key)")

    bucket_name = "consultant-documents"
    file_path = f"docs/{consultant_profile_id}/{sha}.pdf"

    try:
        supabase.storage.from_(bucket_name).upload(
            path=file_path,
            file=raw,
            file_options={"content-type": "application/pdf"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Supabase upload failed: {str(e)}")

    doc = ConsultantDocument(
        consultant_profile_id=consultant_profile_id,
        doc_type=doc_type,
        issuer=issuer,
        issue_date=issue_date,
        expires_at=expires_at,
        bucket=bucket_name,
        file_path=file_path,
        file_hash=sha,
        is_verified=False,
        verification_note=None,
        created_at=_utc_now(),
    )
    session.add(doc)
    session.commit()
    session.refresh(doc)
    return doc


def get_document_public_url(doc: ConsultantDocument) -> str:
    supabase = get_supabase_client()
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured (missing URL/key)")
    return supabase.storage.from_(doc.bucket).get_public_url(doc.file_path)

