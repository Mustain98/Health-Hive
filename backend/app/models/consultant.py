from __future__ import annotations

from datetime import datetime, date, time
from enum import Enum, IntEnum
from typing import Optional

from sqlmodel import SQLModel, Field

from app.models.user_data import utc_now


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


class ConsultantProfile(SQLModel, table=True):
    __tablename__ = "consultant_profiles"

    id: Optional[int] = Field(default=None, primary_key=True, index=True)

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

    bucket: str = Field(default="consultant-documents")
    file_path: str = Field(nullable=False)

    is_verified: bool = Field(default=False, index=True)
    verification_note: Optional[str] = None

    file_hash: Optional[str] = None

    created_at: datetime = Field(default_factory=utc_now)


class Weekday(IntEnum):
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


class ConsultantAvailabilityRule(SQLModel, table=True):
    __tablename__ = "consultant_availability_rules"

    id: Optional[int] = Field(default=None, primary_key=True)

    consultant_profile_id: int = Field(
        foreign_key="consultant_profiles.id",
        index=True,
        nullable=False,
    )

    day_of_week: Weekday = Field(index=True)

    start_time: time
    end_time: time

    timezone: str = Field(default="Asia/Dhaka")

    consultation_duration: int = Field(default=30)

    is_active: bool = Field(default=True, index=True)
