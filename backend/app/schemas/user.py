from __future__ import annotations

from typing import Optional

from sqlmodel import SQLModel

from app.models.user import UserType


class UserLogin(SQLModel):
    # matches auth router: identifier can be email or username
    identifier: str
    password: str


class UserRegister(SQLModel):
    username: Optional[str] = None
    email: str
    password: str
    full_name: Optional[str] = None


class UserRead(SQLModel):
    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    user_type: UserType


class UserUpdate(SQLModel):
    username: Optional[str] = None
    email: Optional[str] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
