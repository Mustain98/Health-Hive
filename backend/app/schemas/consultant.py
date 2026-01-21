from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlmodel import SQLModel

from app.models.consultant import ConsultantType, DocumentType


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



class ConsultantProfileRead(SQLModel):
    id: int
    user_id: int

    display_name: str
    bio: Optional[str] = None
    specialties: Optional[str] = None
    other_info: Optional[str] = None

    consultant_type: ConsultantType

    highest_qualification: str
    graduation_institution: Optional[str] = None

    registration_body: Optional[str] = None
    registration_number: Optional[str] = None

    is_verified: bool
    verified_at: Optional[datetime] = None

    created_at: datetime
    updated_at: datetime



class ConsultantPublicRead(SQLModel):
    id: int
    display_name: str
    bio: Optional[str] = None
    specialties: Optional[str] = None

    consultant_type: ConsultantType
    is_verified: bool



class ConsultantDocumentCreate(SQLModel):
    doc_type: DocumentType

    issuer: Optional[str] = None
    issue_date: Optional[date] = None
    expires_at: Optional[date] = None



class ConsultantDocumentRead(SQLModel):
    id: int
    consultant_profile_id: int

    doc_type: DocumentType
    issuer: Optional[str] = None
    issue_date: Optional[date] = None
    expires_at: Optional[date] = None

    bucket: str
    file_path: str

    is_verified: bool
    verification_note: Optional[str] = None

    created_at: datetime

class ConsultantDocumentReadWithUrl(ConsultantDocumentRead):
    file_url: str
