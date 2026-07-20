from typing import List, Optional
import uuid

from fastapi import HTTPException
from sqlmodel import Session, select

from app.modules.meal.models import FoodItem, FoodItemLabelName
from app.modules.meal.schemas import FoodItemCreate


def get_food_items(
    session: Session,
    query: Optional[str] = None,
    label: Optional[FoodItemLabelName] = None,
    skip: int = 0,
    limit: int = 50,
) -> List[FoodItem]:
    stmt = select(FoodItem)

    if query:
        stmt = stmt.where(FoodItem.name.ilike(f"%{query}%"))

    if label:
        # JSONB containment: labels @> '["<label>"]'
        stmt = stmt.where(FoodItem.labels.contains([label.value]))

    stmt = stmt.order_by(FoodItem.name).offset(skip).limit(limit)
    return list(session.exec(stmt).all())


