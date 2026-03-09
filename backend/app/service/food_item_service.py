from typing import List, Optional
import uuid

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models.meal_plan.food_item import FoodItem, FoodItemLabel, FoodItemLabelName
from app.schemas.food_item_schema import FoodItemCreate


def get_or_create_label(session: Session, name: FoodItemLabelName) -> FoodItemLabel:
    label = session.exec(select(FoodItemLabel).where(FoodItemLabel.name == name)).first()
    if not label:
        label = FoodItemLabel(name=name)
        session.add(label)
        session.commit()
        session.refresh(label)
    return label


def create_food_item(session: Session, data: FoodItemCreate) -> FoodItem:
    # Build core item
    fi = FoodItem(
        name=data.name,
        description=data.description,
        nutrition_unit=data.nutrition_unit,
        weight_per_unit_g=data.weight_per_unit_g,
        calories=data.calories,
        protein_g=data.protein_g,
        carbs_g=data.carbs_g,
        fat_g=data.fat_g,
    )
    
    # Resolve labels
    for lbl_name in data.labels:
        lbl = get_or_create_label(session, lbl_name)
        fi.labels.append(lbl)
        
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
        # Join labels to filter
        stmt = stmt.join(FoodItem.labels).where(FoodItemLabel.name == label)
        
    stmt = stmt.order_by(FoodItem.name).offset(skip).limit(limit)
    return list(session.exec(stmt).all())


def delete_food_item(session: Session, item_id: uuid.UUID) -> None:
    fi = session.get(FoodItem, item_id)
    if not fi:
        raise HTTPException(status_code=404, detail="Food item not found")
        
    # SQLModel will cascade or we can just delete it
    session.delete(fi)
    session.commit()
