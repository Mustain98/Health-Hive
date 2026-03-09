from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import uuid

from pydantic import EmailStr
from sqlmodel import SQLModel, Field



class UserType(str, Enum):
    user = "user"
    consultant = "consultant"
    admin = "admin"




class User(SQLModel, table=True):
    __tablename__ = "users"
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    email: EmailStr = Field(unique=True, index=True)
    username: str = Field(unique=True, index=True)
    full_name: Optional[str] = None
    user_type: UserType = Field(default=UserType.user)
    hashed_password: str


# --- Schemas ---

class UserLogin(SQLModel):
    identifier: str
    password: str


class UserRegister(SQLModel):
    username: Optional[str] = None
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class UserPasswordUpdate(SQLModel):
    old_password:str
    new_password:str

class UserRead(SQLModel):
    id: uuid.UUID
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    user_type: UserType

class UserUpdate(SQLModel):
    username: Optional[str] = None
    email: Optional[EmailStr]=None
    full_name: Optional[str] = None
