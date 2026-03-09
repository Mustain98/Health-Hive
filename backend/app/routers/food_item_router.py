from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.core.auth import get_current_user, require_user_type
from app.core.database import get_session
from app.models.meal_plan.food_item import FoodItemLabelName
from app.models.user import User
from app.schemas.food_item_schema import FoodItemCreate, FoodItemRead
from app.service import food_item_service as svc

router = APIRouter(prefix="/food-items", tags=["Food Items"])


@router.get("", response_model=List[FoodItemRead])
def list_food_items(
    q: Optional[str] = Query(None, description="Search by food name"),
    label: Optional[FoodItemLabelName] = Query(None, description="Filter by a specific label"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """Get all food items, optionally filtered by search text and/or label."""
    return svc.get_food_items(session, query=q, label=label, skip=skip, limit=limit)


