
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, List, Optional
import uuid

from sqlmodel import Field, Relationship, SQLModel


if TYPE_CHECKING:
    from .meal import MealFoodItem


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MeasureUnit(str, Enum):
    gram = "g"
    milliliter = "ml"
    piece = "piece"
    tbsp = "tbsp"



class MacroFields(SQLModel):
    calories: float = Field(default=0, ge=0)
    protein_g: float = Field(default=0, ge=0)
    carbs_g: float = Field(default=0, ge=0)
    fat_g: float = Field(default=0, ge=0)


class FoodItemLabelName(str, Enum):
    grain = "grain"
    meat = "meat"
    fish = "fish"
    dairy = "dairy"
    vegetable = "vegetable"
    fruit = "fruit"
    legume = "legume"
    nut_seed = "nut_seed"
    oil_fat = "oil_fat"
    beverage = "beverage"
    spice = "spice"
    sweetener = "sweetener"

    halal = "halal"
    vegetarian = "vegetarian"
    vegan = "vegan"

    egg = "egg"
    gluten = "gluten"
    nuts = "nuts"
    shellfish = "shellfish"
    soy = "soy"

    high_protein = "high_protein"
    high_fiber = "high_fiber"
    low_carb = "low_carb"
    low_fat = "low_fat"

    other = "other"


class FoodItemLabelLink(SQLModel, table=True):
    __tablename__ = "food_item_label_link"

    food_item_id: uuid.UUID = Field(
        foreign_key="food_item.id",
        primary_key=True,
    )
    food_item_label_id: uuid.UUID = Field(
        foreign_key="food_item_label.id",
        primary_key=True,
    )
    created_at: datetime = Field(default_factory=utc_now)


class FoodItemLabelBase(SQLModel):
    name: FoodItemLabelName = Field(index=True, unique=True)
    description: Optional[str] = None


class FoodItemLabel(FoodItemLabelBase, table=True):
    __tablename__ = "food_item_label"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=utc_now)

    food_items: List["FoodItem"] = Relationship(
        back_populates="labels",
        link_model=FoodItemLabelLink,
    )


class FoodItemBase(MacroFields, SQLModel):
    name: str = Field(index=True, max_length=255)
    description: Optional[str] = None

    # Rule:
    # - if nutrition_unit is gram or milliliter -> nutrition values are per 100 of that unit
    # - if nutrition_unit is piece or tbsp -> nutrition values are per 1 of that unit
    nutrition_unit: MeasureUnit = Field(default=MeasureUnit.gram)

    # Optional helper for conversion:
    # 1 banana -> 118g
    # 1 egg -> 50g
    # 1 tbsp olive oil -> 13.5g
    weight_per_unit_g: Optional[float] = Field(default=None, gt=0)

    is_verified: bool = Field(default=True, index=True)


class FoodItem(FoodItemBase, table=True):
    __tablename__ = "food_item"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    labels: List[FoodItemLabel] = Relationship(
        back_populates="food_items",
        link_model=FoodItemLabelLink,
    )

    meal_food_items: List["MealFoodItem"] = Relationship(
        back_populates="food_item",
    )