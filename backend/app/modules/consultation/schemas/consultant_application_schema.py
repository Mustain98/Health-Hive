from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from app.models import (
    ApplicationStatus,
    ConsultantApplicationDocumentType,
    ConsultantType,
)


class ConsultantApplicationCreate(SQLModel):
    consultant_type: ConsultantType
    full_name: str
    bio: Optional[str] = None
    specialization: Optional[str] = None
    experience_years: int = Field(default=0, ge=0)
    license_number: Optional[str] = None
    organization: Optional[str] = None


class ConsultantApplicationUpdate(SQLModel):
    consultant_type: Optional[ConsultantType] = None
    full_name: Optional[str] = None
    bio: Optional[str] = None
    specialization: Optional[str] = None
    experience_years: Optional[int] = Field(default=None, ge=0)
    license_number: Optional[str] = None
    organization: Optional[str] = None


class ConsultantApplicationRead(SQLModel):
    id: str
    user_id: str
    consultant_type: ConsultantType
    full_name: str
    bio: Optional[str] = None
    specialization: Optional[str] = None
    experience_years: int
    license_number: Optional[str] = None
    organization: Optional[str] = None
    status: ApplicationStatus
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ConsultantApplicationDocumentRead(SQLModel):
    id: str
    application_id: str
    document_type: ConsultantApplicationDocumentType
    file_url: str
    file_name: Optional[str] = None
    content_type: Optional[str] = None
    file_size: Optional[int] = None
    uploaded_at: datetime


class MessageResponse(SQLModel):
    message: str