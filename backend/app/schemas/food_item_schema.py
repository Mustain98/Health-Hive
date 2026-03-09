from typing import List, Optional
import uuid

from pydantic import BaseModel, ConfigDict
from app.models.meal_plan.food_item import FoodItemLabelName, MeasureUnit


class FoodItemCreate(BaseModel):
    name: str
    description: Optional[str] = None
    nutrition_unit: MeasureUnit = MeasureUnit.gram
    weight_per_unit_g: Optional[float] = None
    
    calories: float = 0
    protein_g: float = 0
    carbs_g: float = 0
    fat_g: float = 0
    
    labels: List[FoodItemLabelName] = []


class FoodItemLabelRead(BaseModel):
    id: uuid.UUID
    name: FoodItemLabelName
    description: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class FoodItemRead(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    nutrition_unit: MeasureUnit
    weight_per_unit_g: Optional[float] = None
    
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    
    is_verified: bool
    labels: List[FoodItemLabelRead] = []
    
    model_config = ConfigDict(from_attributes=True)
