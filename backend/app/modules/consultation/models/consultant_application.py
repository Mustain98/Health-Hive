from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import uuid

from sqlmodel import Field, Relationship, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ConsultantType(str, Enum):
    nutritionist = "nutritionist"
    dietitian = "dietitian"
    fitness_trainer = "fitness_trainer"
    doctor = "doctor"
    mental_health = "mental_health"
    other = "other"


class ApplicationStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class ConsultantApplicationDocumentType(str, Enum):
    cv = "cv"
    certificate = "certificate"
    license = "license"
    nid = "nid"
    other = "other"


class ConsultantDocumentType(str, Enum):
    profile_photo = "profile_photo"
    certificate = "certificate"
    license = "license"
    portfolio = "portfolio"
    other = "other"


class ConsultantApplication(SQLModel, table=True):
    __tablename__ = "consultant_applications"

    id: str = Field(
        primary_key=True,
        default_factory=lambda: str(uuid.uuid4()),
    )

    user_id: str = Field(
        foreign_key="users.id",
        index=True,
    )

    consultant_type: ConsultantType = Field(index=True)

    full_name: str = Field(nullable=False)
    bio: Optional[str] = None
    specialization: Optional[str] = None

    experience_years: int = Field(default=0, ge=0)

    license_number: Optional[str] = Field(default=None, index=True)
    organization: Optional[str] = None

    status: ApplicationStatus = Field(
        default=ApplicationStatus.pending,
        index=True,
    )

    rejection_reason: Optional[str] = None

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    documents: list["ConsultantApplicationDocument"] = Relationship(
        back_populates="application"
    )


class ConsultantApplicationDocument(SQLModel, table=True):
    __tablename__ = "consultant_application_documents"

    id: str = Field(
        primary_key=True,
        default_factory=lambda: str(uuid.uuid4()),
    )

    application_id: str = Field(
        foreign_key="consultant_applications.id",
        index=True,
    )

    public_id: str = Field(nullable=False, index=True)
    resource_type: str = Field(default="raw", index=True)

    document_type: ConsultantApplicationDocumentType = Field(index=True)

    file_url: str = Field(nullable=False)
    file_name: Optional[str] = None

    # examples: application/pdf, image/png, image/jpeg
    content_type: Optional[str] = None

    file_size: Optional[int] = Field(default=None, ge=0)

    uploaded_at: datetime = Field(default_factory=utc_now)

    application: Optional["ConsultantApplication"] = Relationship(
        back_populates="documents"
    )


