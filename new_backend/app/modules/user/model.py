from enum import Enum
from typing import Optional
import uuid

from sqlmodel import SQLModel, Field, Relationship


class Gender(str, Enum):
    male = "male"
    female = "female"


class ActivityLevel(str, Enum):
    sedentary = "sedentary"
    lightly_active = "lightly_active"
    moderately_active = "moderately_active"
    very_active = "very_active"
    extra_active = "extra_active"

class Role(str,Enum):
    user="user"
    consultant="consultant"

class User(SQLModel, table=True):
    __tablename__ = "users"

    id: str = Field(
        primary_key=True,
        default_factory=lambda: str(uuid.uuid4())
    )

    username: str = Field(nullable=False,unique=True,index=True)
    email: str = Field(nullable=False, unique=True, index=True)
    password: str = Field(nullable=False)
    role:Role = Field(default=Role.user)
    is_active: bool = Field(nullable=False, default=True)
    user_data: Optional["UserData"] = Relationship(back_populates="user")


class UserData(SQLModel, table=True):
    __tablename__ = "user_data"

    user_id: str = Field(
        primary_key=True,
        foreign_key="users.id",
        index=True,
    )

    age: int = Field(default=0)
    height: float = Field(default=0.0)
    weight: float = Field(default=0.0)

    gender: Optional[Gender] = Field(default=None, index=True)
    activity_level: Optional[ActivityLevel] = Field(default=None, index=True)

    user: Optional[User] = Relationship(back_populates="user_data")