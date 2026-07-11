from typing import List, Optional
import uuid

from fastapi import HTTPException
from sqlmodel import Session, select

from app.modules.meal.models import FoodItem, FoodItemLabelName
from app.modules.meal.schemas import FoodItemCreate


def create_food_item(session: Session, data: FoodItemCreate) -> FoodItem:
    fi = FoodItem(
        name=data.name,
        description=data.description,
        nutrition_unit=data.nutrition_unit,
        weight_per_unit_g=data.weight_per_unit_g,
        calories=data.calories,
        protein_g=data.protein_g,
        carbs_g=data.carbs_g,
        fat_g=data.fat_g,
        labels=[lbl.value for lbl in data.labels],
    )

    session.add(fi)
    session.commit()
    session.refresh(fi)
    return fi


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


def delete_food_item(session: Session, item_id: uuid.UUID) -> None:
    fi = session.get(FoodItem, item_id)
    if not fi:
        raise HTTPException(status_code=404, detail="Food item not found")

    session.delete(fi)
    session.commit()
