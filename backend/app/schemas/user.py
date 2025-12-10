from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import EmailStr
from sqlmodel import SQLModel


class UserRegister(SQLModel):
    email: EmailStr
    password: str
    username: Optional[str] = None
    full_name: Optional[str] = None 

class UserRead(SQLModel):
    id: int
    username: str
    email: EmailStr
    full_name: Optional[str]
    created_at: datetime
    updated_at: datetime

class UserUpdate(SQLModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    full_name: Optional[str] = None 

class UserLogin(SQLModel):
    identifier: str  
    password: str

