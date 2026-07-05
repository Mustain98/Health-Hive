from typing import Optional
from sqlmodel import SQLModel


class PlanCreate(SQLModel):
    name: Optional[str] = None
    source: Optional[str] = None  # self | ai | consultant (defaults to self)


class PlanRename(SQLModel):
    name: str
