from __future__ import annotations

from datetime import datetime, date
from enum import Enum
from typing import Optional

from sqlmodel import SQLModel, Field
from sqlalchemy import Column
from sqlalchemy.types import LargeBinary

from app.models.user_data import utc_now


class StorageKind(str, Enum):
    local = "local"
    s3 = "s3"
    db = "db"


class ConsultantProfile(SQLModel, table=True):
    __tablename__ = "consultant_profiles"

    id: Optional[int] = Field(default=None, primary_key=True, index=True)

    user_id: int = Field(foreign_key="users.id", index=True, unique=True)

    # search by name
    display_name: str = Field(index=True)

    bio: Optional[str] = None
    specialties: Optional[str] = None
    other_info: Optional[str] = None

    is_verified: bool = Field(default=False, index=True)

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ConsultantDocument(SQLModel, table=True):
    __tablename__ = "consultant_documents"

    id: Optional[int] = Field(default=None, primary_key=True, index=True)

    consultant_profile_id: int = Field(
        foreign_key="consultant_profiles.id",
        index=True,
    )

    doc_type: str = Field(default="certificate", index=True)  # certificate/license/etc.
    title: str
    issuer: Optional[str] = None
    issue_date: Optional[date] = None
    expires_at: Optional[date] = None

    mime_type: str = Field(default="application/pdf")

    storage_kind: StorageKind = Field(default=StorageKind.local, index=True)

    # For local/S3
    file_url: Optional[str] = None
    file_path: Optional[str] = None

    # For DB storage (BYTEA)
    file_bytes: Optional[bytes] = Field(
        default=None,
        sa_column=Column(LargeBinary, nullable=True),
    )

    file_size_bytes: Optional[int] = None
    file_sha256: Optional[str] = Field(default=None, index=True)

    created_at: datetime = Field(default_factory=utc_now)
