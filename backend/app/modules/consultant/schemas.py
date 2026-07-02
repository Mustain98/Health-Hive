from __future__ import annotations

from datetime import datetime, date
from enum import Enum
from typing import Optional
import uuid

from sqlmodel import SQLModel


# ── Enums ──────────────────────────────────────────────────────────────────

class ConsultantType(str, Enum):
    clinical = "clinical"
    non_clinical = "non_clinical"
    wellness = "wellness"


class DocumentType(str, Enum):
    degree = "degree"
    certificate = "certificate"
    license = "license"
    internship = "internship"
    experience = "experience"


class ApplicationStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


# ── Schemas ────────────────────────────────────────────────────────────────

class ConsultantPublicRead(SQLModel):
    user_id: uuid.UUID  # primary key (used as the consultant's public ID)
    display_name: str
    bio: Optional[str] = None
    specialties: Optional[str] = None
    other_info: Optional[str] = None
    consultant_type: ConsultantType
    highest_qualification: str
    graduation_institution: Optional[str] = None
    is_verified: bool


class ConsultantProfileCreate(SQLModel):
    display_name: str
    bio: Optional[str] = None
    specialties: Optional[str] = None
    other_info: Optional[str] = None
    consultant_type: ConsultantType
    highest_qualification: str
    graduation_institution: Optional[str] = None
    registration_body: Optional[str] = None
    registration_number: Optional[str] = None


class ConsultantProfileUpdate(SQLModel):
    display_name: Optional[str] = None
    bio: Optional[str] = None
    specialties: Optional[str] = None
    other_info: Optional[str] = None
    consultant_type: Optional[ConsultantType] = None
    highest_qualification: Optional[str] = None
    graduation_institution: Optional[str] = None
    registration_body: Optional[str] = None
    registration_number: Optional[str] = None


class ConsultantDocumentCreate(SQLModel):
    doc_type: DocumentType
    issuer: Optional[str] = None
    issue_date: Optional[date] = None
    expires_at: Optional[date] = None


class ConsultantDocumentReadWithUrl(SQLModel):
    id: uuid.UUID
    consultant_profile_id: uuid.UUID
    doc_type: DocumentType
    issuer: Optional[str] = None
    issue_date: Optional[date] = None
    expires_at: Optional[date] = None
    bucket: str
    file_path: str
    is_verified: bool
    verification_note: Optional[str] = None
    created_at: datetime
    file_url: str
