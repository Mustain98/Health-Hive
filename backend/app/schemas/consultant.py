from __future__ import annotations

from datetime import date, datetime
from typing import Optional, List

from sqlmodel import SQLModel

from app.models.consultant import StorageKind


class ConsultantProfileCreate(SQLModel):
    display_name: str
    bio: Optional[str] = None
    specialties: Optional[str] = None
    other_info: Optional[str] = None


class ConsultantProfileUpdate(SQLModel):
    display_name: Optional[str] = None
    bio: Optional[str] = None
    specialties: Optional[str] = None
    other_info: Optional[str] = None


class ConsultantProfileRead(SQLModel):
    id: int
    user_id: int
    display_name: str
    bio: Optional[str] = None
    specialties: Optional[str] = None
    other_info: Optional[str] = None
    is_verified: bool
    created_at: datetime
    updated_at: datetime


class ConsultantPublicRead(SQLModel):
    id: int
    user_id: int
    display_name: str
    bio: Optional[str] = None
    specialties: Optional[str] = None
    is_verified: bool


class ConsultantDocumentCreate(SQLModel):
    doc_type: str = "certificate"
    title: str
    issuer: Optional[str] = None
    issue_date: Optional[date] = None
    expires_at: Optional[date] = None


class ConsultantDocumentRead(SQLModel):
    id: int
    consultant_profile_id: int
    doc_type: str
    title: str
    issuer: Optional[str] = None
    issue_date: Optional[date] = None
    expires_at: Optional[date] = None
    mime_type: str
    storage_kind: StorageKind
    file_url: Optional[str] = None
    file_path: Optional[str] = None
    file_size_bytes: Optional[int] = None
    file_sha256: Optional[str] = None
    created_at: datetime
