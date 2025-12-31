from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import EmailStr
from sqlmodel import SQLModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)



class UserType(str, Enum):
    user = "user"
    consultant = "consultant"


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True, index=True)

    username: str = Field(index=True, unique=True)
    email: str = Field(index=True, unique=True)
    full_name: Optional[str] = Field(default=None)

    hashed_password: str

    user_type: UserType = Field(default=UserType.user, index=True)
