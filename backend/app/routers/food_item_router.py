from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.core.auth import get_current_user, require_user_type
from app.core.database import get_session
from app.models.meal_plan.food_item import FoodItemLabelName
from app.models.user import User
from app.models.user_data import UserAllergen, UserPreference
from app.models.meal_plan.food_item import FoodItem
from app.schemas.food_item_schema import FoodItemCreate, FoodItemRead
from app.service import food_item_service as svc
from sqlmodel import select
from fastapi import HTTPException

router = APIRouter(prefix="/food-items", tags=["Food Items"])


@router.get("", response_model=List[FoodItemRead])
def list_food_items(
    q: Optional[str] = Query(None, description="Search by food name"),
    label: Optional[FoodItemLabelName] = Query(None, description="Filter by a specific label"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """Get all food items, optionally filtered by search text and/or label."""
    return svc.get_food_items(session, query=q, label=label, skip=skip, limit=limit)


# ── Allergens ─────────────────────────────────────────────────────────────────

@router.get("/allergens", response_model=List[FoodItemRead])
def get_user_allergens(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """Get all food items the current user has marked as allergens."""
    stmt = (
        select(FoodItem)
        .join(UserAllergen, UserAllergen.food_item_id == FoodItem.id)
        .where(UserAllergen.user_id == me.id)
        .offset(skip)
        .limit(limit)
    )
    allergens = session.exec(stmt).all()
    return allergens


@router.post("/{food_item_id}/allergen")
def add_allergen(
    food_item_id: uuid.UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """Mark a specific food item as an allergen for the user."""
    food_item = session.get(FoodItem, food_item_id)
    if not food_item:
        raise HTTPException(status_code=404, detail="Food item not found")
        
    allergen = session.get(UserAllergen, (me.id, food_item_id))
    if not allergen:
        allergen = UserAllergen(user_id=me.id, food_item_id=food_item_id)
        session.add(allergen)
        session.commit()
    return {"message": "Allergen added successfully"}


@router.delete("/{food_item_id}/allergen")
def remove_allergen(
    food_item_id: uuid.UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """Remove a specific food item from the user's allergens."""
    allergen = session.get(UserAllergen, (me.id, food_item_id))
    if allergen:
        session.delete(allergen)
        session.commit()
    return {"message": "Allergen removed successfully"}


# ── Preferences ───────────────────────────────────────────────────────────────

@router.get("/preferences", response_model=List[FoodItemRead])
def get_user_preferences(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """Get all food items the current user has marked as preferred."""
    stmt = (
        select(FoodItem)
        .join(UserPreference, UserPreference.food_item_id == FoodItem.id)
        .where(UserPreference.user_id == me.id)
        .offset(skip)
        .limit(limit)
    )
    preferences = session.exec(stmt).all()
    return preferences


@router.post("/{food_item_id}/preference")
def add_preference(
    food_item_id: uuid.UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """Mark a specific food item as a preference for the user."""
    food_item = session.get(FoodItem, food_item_id)
    if not food_item:
        raise HTTPException(status_code=404, detail="Food item not found")
        
    preference = session.get(UserPreference, (me.id, food_item_id))
    if not preference:
        preference = UserPreference(user_id=me.id, food_item_id=food_item_id)
        session.add(preference)
        session.commit()
    return {"message": "Preference added successfully"}


@router.delete("/{food_item_id}/preference")
def remove_preference(
    food_item_id: uuid.UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """Remove a specific food item from the user's preferences."""
    preference = session.get(UserPreference, (me.id, food_item_id))
    if preference:
        session.delete(preference)
        session.commit()
    return {"message": "Preference removed successfully"}

