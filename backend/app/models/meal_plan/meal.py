from datetime import datetime, time, timezone
from enum import Enum
from typing import TYPE_CHECKING, List, Optional
import uuid

from sqlmodel import Field, Relationship, SQLModel

from .food_item import MacroFields, MeasureUnit


if TYPE_CHECKING:
    from .food_item import FoodItem
    from .plan import DayMealPlan


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MealLabelName(str, Enum):
    breakfast = "breakfast"
    lunch = "lunch"
    dinner = "dinner"
    snack = "snack"

    main_meal = "main_meal"
    side_meal = "side_meal"
    drink = "drink"
    dessert = "dessert"

    halal = "halal"
    vegetarian = "vegetarian"
    vegan = "vegan"

    high_protein = "high_protein"
    low_carb = "low_carb"
    gym_friendly = "gym_friendly"

    other = "other"


class MealTimeType(str, Enum):
    breakfast = "breakfast"
    lunch = "lunch"
    dinner = "dinner"
    snack = "snack"


class MealLabelLink(SQLModel, table=True):
    __tablename__ = "meal_label_link"

    meal_id: uuid.UUID = Field(
        foreign_key="meal.id",
        primary_key=True,
    )
    meal_label_id: uuid.UUID = Field(
        foreign_key="meal_label.id",
        primary_key=True,
    )
    created_at: datetime = Field(default_factory=utc_now)


class MealFoodItemBase(SQLModel):
    quantity: float = Field(gt=0)
    unit: MeasureUnit = Field(default=MeasureUnit.gram)


class MealFoodItem(MealFoodItemBase, table=True):
    __tablename__ = "meal_food_item"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    meal_id: uuid.UUID = Field(foreign_key="meal.id", index=True)
    food_item_id: uuid.UUID = Field(foreign_key="food_item.id", index=True)

    created_at: datetime = Field(default_factory=utc_now)

    meal: Optional["Meal"] = Relationship(back_populates="meal_food_items")
    food_item: Optional["FoodItem"] = Relationship(back_populates="meal_food_items")


class MealBase(MacroFields, SQLModel):
    name: str = Field(index=True, max_length=255)
    description: Optional[str] = None
    instructions: Optional[str] = None
    image_url: Optional[str] = None

    servings: float = Field(default=1, gt=0)
    total_weight_g: Optional[float] = Field(default=None, gt=0)

    is_verified: bool = Field(default=True, index=True)


class Meal(MealBase, table=True):
    __tablename__ = "meal"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    meal_food_items: List["MealFoodItem"] = Relationship(
        back_populates="meal",
    )

    labels: List["MealLabel"] = Relationship(
        back_populates="meals",
        link_model=MealLabelLink,
    )

    combo_items: List["MealComboItem"] = Relationship(
        back_populates="meal",
    )


class MealLabelBase(SQLModel):
    name: MealLabelName = Field(index=True, unique=True)
    description: Optional[str] = None


class MealLabel(MealLabelBase, table=True):
    __tablename__ = "meal_label"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    meals: List["Meal"] = Relationship(
        back_populates="labels",
        link_model=MealLabelLink,
    )


class MealComboBase(MacroFields, SQLModel):
    name: str = Field(index=True, max_length=255)
    description: Optional[str] = None
    meal_time: MealTimeType = Field(index=True)

    servings: float = Field(default=1, gt=0)
    total_weight_g: Optional[float] = Field(default=None, gt=0)



class MealCombo(MealComboBase, table=True):
    __tablename__ = "meal_combo"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    combo_items: List["MealComboItem"] = Relationship(
        back_populates="meal_combo"
    )
    timed_meals: List["TimedMeal"] = Relationship(
        back_populates="meal_combo"
    )


class MealComboItem(SQLModel, table=True):
    __tablename__ = "meal_combo_item"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    meal_combo_id: uuid.UUID = Field(foreign_key="meal_combo.id", index=True)
    meal_id: uuid.UUID = Field(foreign_key="meal.id", index=True)

    quantity: float = Field(default=1, gt=0)
    note: Optional[str] = None

    created_at: datetime = Field(default_factory=utc_now)

    meal_combo: Optional["MealCombo"] = Relationship(back_populates="combo_items")
    meal: Optional["Meal"] = Relationship(back_populates="combo_items")


class TimedMealBase(MacroFields, SQLModel):
    meal_time: MealTimeType = Field(index=True)
    scheduled_time: Optional[time] = None
    note: Optional[str] = None


class TimedMeal(TimedMealBase, table=True):
    __tablename__ = "timed_meal"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    day_plan_id: uuid.UUID = Field(foreign_key="day_meal_plan.id", index=True)
    meal_combo_id: uuid.UUID = Field(foreign_key="meal_combo.id", index=True)

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    day_plan: Optional["DayMealPlan"] = Relationship(back_populates="timed_meals")
    meal_combo: Optional["MealCombo"] = Relationship(back_populates="timed_meals")