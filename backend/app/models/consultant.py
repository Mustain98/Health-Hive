from __future__ import annotations

from datetime import datetime, date, time
from enum import Enum, IntEnum
from typing import Optional
import uuid

from sqlmodel import SQLModel, Field

from app.utils.time import utc_now


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

    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    day_of_week: Weekday = Field(index=True)
    start_time: time
    end_time: time
    timezone: str = Field(default="Asia/Dhaka")
    consultation_duration: int = Field(default=30)
    is_active: bool = Field(default=True, index=True)
    consultant_profile_id: uuid.UUID = Field(
        foreign_key="consultant_profiles.user_id",
        index=True,
        nullable=False,
    )


# --- Schemas ---


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


class AvailabilityRuleCreate(SQLModel):
    day_of_week: int  # 0-6 (Monday-Sunday)
    start_time: str   # HH:MM format
    end_time: str     # HH:MM format
    timezone: str = "Asia/Dhaka"
    consultation_duration: int = 30




class AvailabilityRuleUpdate(SQLModel):
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    consultation_duration: Optional[int] = None
    is_active: Optional[bool] = None
