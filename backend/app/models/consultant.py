from __future__ import annotations

from datetime import datetime, date
from enum import Enum
from typing import Optional

from sqlmodel import SQLModel, Field

from app.models.user_data import utc_now


# =========================
# ENUMS
# =========================

class ConsultantType(str, Enum):
    CLINICAL = "clinical"
    NON_CLINICAL = "non_clinical"
    WELLNESS = "wellness"


class DocumentType(str, Enum):
    DEGREE = "degree"
    CERTIFICATE = "certificate"
    LICENSE = "license"
    INTERNSHIP = "internship"
    EXPERIENCE = "experience"


# =========================
# CONSULTANT PROFILE
# =========================

class ConsultantProfile(SQLModel, table=True):
    __tablename__ = "consultant_profiles"

    id: Optional[int] = Field(default=None, primary_key=True, index=True)

    # One-to-one with users table
    user_id: int = Field(
        foreign_key="users.id",
        unique=True,
        index=True,
        nullable=False,
    )

    display_name: str = Field(index=True)

    bio: Optional[str] = None
    specialties: Optional[str] = None
    other_info: Optional[str] = None

    # Professional info
    consultant_type: ConsultantType = Field(index=True)

    highest_qualification: str = Field(
        description="e.g. BSc in Nutrition, MSc in Public Health Nutrition"
    )
    graduation_institution: Optional[str] = Field(index=True)

    registration_body: Optional[str] = Field(
        description="e.g. Bangladesh Nutrition Society"
    )
    registration_number: Optional[str] = Field(index=True)

    # Verification
    is_verified: bool = Field(default=False, index=True)
    verified_at: Optional[datetime] = None

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


# =========================
# CONSULTANT DOCUMENTS
# =========================

class ConsultantDocument(SQLModel, table=True):
    __tablename__ = "consultant_documents"

    id: Optional[int] = Field(default=None, primary_key=True, index=True)

    consultant_profile_id: int = Field(
        foreign_key="consultant_profiles.id",
        index=True,
        nullable=False,
    )

    doc_type: DocumentType = Field(index=True)

    issuer: Optional[str] = None
    issue_date: Optional[date] = None
    expires_at: Optional[date] = None

    # Supabase Storage info
    bucket: str = Field(default="consultant-documents")
    file_path: str = Field(
        nullable=False,
        description="Path inside Supabase bucket"
    )

    # Verification per document
    is_verified: bool = Field(default=False, index=True)
    verification_note: Optional[str] = None

    # Integrity
    file_hash: Optional[str] = Field(
        description="SHA256 hash of uploaded file"
    )

    created_at: datetime = Field(default_factory=utc_now)
