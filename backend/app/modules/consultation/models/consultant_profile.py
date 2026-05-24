from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import uuid

from sqlmodel import Field, Relationship, SQLModel
from app.models import ConsultantType,ConsultantDocumentType

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class ConsultantProfile(SQLModel, table=True):
    __tablename__ = "consultant_profiles"

    user_id: str = Field(
        primary_key=True,
        foreign_key="users.id",
        index=True,
    )

    consultant_type: ConsultantType = Field(index=True)

    full_name: str = Field(nullable=False)
    bio: Optional[str] = None
    specialization: Optional[str] = None

    experience_years: int = Field(default=0, ge=0)
    consultation_fee: float = Field(default=0.0, ge=0)

    license_number: Optional[str] = Field(default=None, index=True)
    organization: Optional[str] = None

    is_available: bool = Field(default=True, index=True)

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    documents: list["ConsultantDocument"] = Relationship(
        back_populates="consultant_profile"
    )


class ConsultantDocument(SQLModel, table=True):
    __tablename__ = "consultant_documents"

    id: str = Field(
        primary_key=True,
        default_factory=lambda: str(uuid.uuid4()),
    )

    consultant_profile_id: str = Field(
        foreign_key="consultant_profiles.user_id",
        index=True,
    )

    public_id: str = Field(nullable=False, index=True)
    resource_type: str = Field(default="raw", index=True)

    document_type: ConsultantDocumentType = Field(index=True)

    file_url: str = Field(nullable=False)
    file_name: Optional[str] = None

    # examples: application/pdf, image/png, image/jpeg
    content_type: Optional[str] = None

    file_size: Optional[int] = Field(default=None, ge=0)

    is_public: bool = Field(default=False, index=True)
    is_verified: bool = Field(default=False, index=True)

    uploaded_at: datetime = Field(default_factory=utc_now)

    consultant_profile: Optional["ConsultantProfile"] = Relationship(
        back_populates="documents"
    )
