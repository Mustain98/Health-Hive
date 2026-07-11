from __future__ import annotations

from datetime import datetime, date
from typing import Optional
import uuid

from sqlmodel import SQLModel, Field

from app.utils.time import utc_now

# Re-export enums + schemas so `from app.modules.consultant.models import X` keeps working
from .schemas import *  # noqa: F401,F403
from .schemas import ConsultantType, DocumentType, ApplicationStatus


class ConsultantApplication(SQLModel, table=True):
    __tablename__ = "consultant_applications"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True, nullable=False, unique=True)

    display_name: str
    bio: Optional[str] = None
    specialties: Optional[str] = None
    other_info: Optional[str] = None
    consultant_type: ConsultantType
    highest_qualification: str
    graduation_institution: Optional[str] = None
    registration_body: Optional[str] = None
    registration_number: Optional[str] = None

    status: ApplicationStatus = Field(default=ApplicationStatus.pending, index=True)
    admin_note: Optional[str] = None

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ApplicationDocument(SQLModel, table=True):
    __tablename__ = "application_documents"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    application_id: uuid.UUID = Field(foreign_key="consultant_applications.id", index=True)
    doc_type: DocumentType
    issuer: Optional[str] = None
    issue_date: Optional[date] = None
    expires_at: Optional[date] = None
    file_path: str
    bucket: str = Field(default="application-documents")
    created_at: datetime = Field(default_factory=utc_now)


class ConsultantProfile(SQLModel, table=True):
    __tablename__ = "consultant_profiles"

    user_id: uuid.UUID = Field(
        foreign_key="users.id",
        primary_key=True,
        nullable=False,
    )
    display_name: str = Field(index=True)
    bio: Optional[str] = None
    specialties: Optional[str] = None
    other_info: Optional[str] = None
    consultant_type: ConsultantType = Field(index=True)
    highest_qualification: str
    graduation_institution: Optional[str] = Field(default=None, index=True)
    registration_body: Optional[str] = None
    registration_number: Optional[str] = Field(default=None, index=True)
    is_verified: bool = Field(default=False, index=True)
    verified_at: Optional[datetime] = None

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ConsultantDocument(SQLModel, table=True):
    __tablename__ = "consultant_documents"

    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    doc_type: DocumentType = Field(index=True)
    issuer: Optional[str] = None
    issue_date: Optional[date] = None
    expires_at: Optional[date] = None
    bucket: str = Field(default="consultant-documents")
    file_path: str = Field(nullable=False)
    is_verified: bool = Field(default=False, index=True)
    verification_note: Optional[str] = None
    file_hash: Optional[str] = None
    consultant_profile_id: uuid.UUID = Field(
        foreign_key="consultant_profiles.user_id",
        index=True,
        nullable=False,
    )

    created_at: datetime = Field(default_factory=utc_now)
