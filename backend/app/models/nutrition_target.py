from datetime import datetime, date
from typing import Optional
import uuid

from sqlmodel import SQLModel, Field

from app.utils.time import utc_now  



class NutritionTarget(SQLModel, table=True):
    __tablename__ = "nutrition_targets"

    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    created_for: uuid.UUID = Field(foreign_key="users.id", index=True)
    created_by: uuid.UUID = Field(foreign_key="users.id", index=True)
    appointment_id:Optional[uuid.UUID]=Field(foreign_key="appointments.id",default=None,index=True)
    active:bool=Field(default=False,nullable=False)
    calories_kcal: int = Field(ge=800, le=10000)
    protein_g: float = Field(ge=0, le=400)
    carbs_g: float = Field(ge=0, le=1200)
    fat_g: float = Field(ge=0, le=300)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class NutritionTargetUpdate(SQLModel):
    calories_kcal: Optional[int] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    active: bool = False

