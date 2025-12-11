from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import EmailStr
from sqlmodel import SQLModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)



class UserBase(SQLModel):
    username: str = Field(index=True, unique=True, max_length=50)
    email: EmailStr = Field(index=True, unique=True, max_length=255)
    full_name: Optional[str] = Field(default=None, max_length=120)


class User(UserBase, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str = Field(max_length=255)

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
