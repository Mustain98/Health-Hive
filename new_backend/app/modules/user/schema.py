from sqlmodel import SQLModel
from model import Role,Gender,ActivityLevel
from typing import Optional

class UserRegister(SQLModel):
    username:str
    email:str
    password:str

class UserLogin(SQLModel):
    identifier:str
    password:str

class TokenResponse(SQLModel):
    access_token: str
    token_type: str = "bearer"

class UserRead(SQLModel):
    id: str
    username: str
    email: str
    role: Role
    is_active: bool


class UserUpdate(SQLModel):
    username: Optional[str] = None
    email: Optional[str] = None

class UpdatePassword(SQLModel):
    old_password:str
    new_password:str
    confirm_password:str

class UserDataRead(SQLModel):
    user_id: str
    age: int
    height: float
    weight: float
    gender: Optional[Gender] = None
    activity_level: Optional[ActivityLevel] = None


class UserDataUpdate(SQLModel):
    age: Optional[int] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    gender: Optional[Gender] = None
    activity_level: Optional[ActivityLevel] = None


class MessageResponse(SQLModel):
    message: str