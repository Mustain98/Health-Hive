from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, UploadFile
from sqlmodel import Session, select

from app.models.consultant import ConsultantProfile, ConsultantDocument, StorageKind
from app.models.user import User, UserType


def _utc_now():
    return datetime.now(timezone.utc)


def _ensure_user_is_consultant(session: Session, user: User) -> User:
    if user.user_type != UserType.consultant:
        user.user_type = UserType.consultant
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


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
) -> ConsultantProfile:
    # _ensure_user_is_consultant(session, me)  <-- Removed auto-promotion

    p = get_profile_by_user_id(session, me.id)
    now = _utc_now()
    if not p:
        p = ConsultantProfile(
            user_id=me.id,
            display_name=display_name,
            bio=bio,
            specialties=specialties,
            other_info=other_info,
            is_verified=False,
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
) -> ConsultantProfile:
    # _ensure_user_is_consultant(session, me)

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


def add_document_local(
    session: Session,
    me: User,
    consultant_profile_id: int,
    *,
    doc_type: str,
    title: str,
    issuer: Optional[str],
    issue_date,
    expires_at,
    file: UploadFile,
    upload_dir: str = "uploads",
) -> ConsultantDocument:
    # ownership check
    profile = session.get(ConsultantProfile, consultant_profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Consultant profile not found")
    if profile.user_id != me.id:
        raise HTTPException(status_code=403, detail="Not your profile")

    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    now = _utc_now()
    os.makedirs(upload_dir, exist_ok=True)
    subdir = os.path.join(upload_dir, "consultants", str(consultant_profile_id))
    os.makedirs(subdir, exist_ok=True)

    raw = file.file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")

    sha = hashlib.sha256(raw).hexdigest()
    filename = f"{sha}.pdf"
    path = os.path.join(subdir, filename)

    with open(path, "wb") as f:
        f.write(raw)

    doc = ConsultantDocument(
        consultant_profile_id=consultant_profile_id,
        doc_type=doc_type,
        title=title,
        issuer=issuer,
        issue_date=issue_date,
        expires_at=expires_at,
        mime_type="application/pdf",
        storage_kind=StorageKind.local,
        file_path=path,
        file_url=None,
        file_bytes=None,
        file_size_bytes=len(raw),
        file_sha256=sha,
        created_at=now,
    )
    session.add(doc)
    session.commit()
    session.refresh(doc)
    return doc
