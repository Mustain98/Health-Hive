from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import uuid

from sqlmodel import SQLModel, Field
from app.utils.time import utc_now



class Gender(str, Enum):
    male = "male"
    female = "female"


class ActivityLevel(str, Enum):
    sedentary = "sedentary"
    light = "light"
    moderate = "moderate"
    active = "active"
    very_active = "very_active"



class UserData(SQLModel, table=True):
    __tablename__ = "user_data"

    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    age: Optional[int] = Field(default=None, ge=10, le=120)
    gender: Optional[Gender] = None   

    height_cm: Optional[float] = Field(default=None, ge=50, le=260)
    weight_kg: Optional[float] = Field(default=None, ge=20, le=400)

    activity_level: Optional[ActivityLevel] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class UserGoalLog(SQLModel,table=True):
    __tablename__="user_goal_logs"
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    goal_id: uuid.UUID = Field(foreign_key="user_goals.id", index=True)
    date:datetime = Field(default_factory=utc_now)
    weight:float= Field(nullable=False)
    due_terget:float =Field(default=0.0)


class UserGoalLogCreate(SQLModel):
    weight: float
    date: Optional[datetime] = None  # defaults to today in service
