from datetime import date, datetime, time, timezone
from enum import Enum
from typing import TYPE_CHECKING, List, Optional
import uuid

from sqlalchemy import JSON, Column
from sqlmodel import Field, Relationship, SQLModel


if TYPE_CHECKING:
    from app.modules.user.models import User


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ── Enums ──────────────────────────────────────────────────────────────────

class MeasureUnit(str, Enum):
    gram = "g"
    milliliter = "ml"
    piece = "piece"
    tbsp = "tbsp"


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


class PlanStatus(str, Enum):
    draft = "draft"
    active = "active"
    completed = "completed"


# ── Shared base ────────────────────────────────────────────────────────────

class MacroFields(SQLModel):
    calories: float = Field(default=0, ge=0)
    protein_g: float = Field(default=0, ge=0)
    carbs_g: float = Field(default=0, ge=0)
    fat_g: float = Field(default=0, ge=0)


# ── Food items ─────────────────────────────────────────────────────────────

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


# ── Meals ──────────────────────────────────────────────────────────────────

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
    meal_combo_id: Optional[uuid.UUID] = Field(default=None, foreign_key="meal_combo.id", index=True)

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    day_plan: Optional["DayMealPlan"] = Relationship(back_populates="timed_meals")
    meal_combo: Optional["MealCombo"] = Relationship(back_populates="timed_meals")
    combo_options: List["TimedMealComboOption"] = Relationship(back_populates="timed_meal")


class TimedMealComboOption(SQLModel, table=True):
    __tablename__ = "timed_meal_combo_option"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    timed_meal_id: uuid.UUID = Field(foreign_key="timed_meal.id", index=True)
    meal_combo_id: uuid.UUID = Field(foreign_key="meal_combo.id", index=True)

    is_chosen: bool = Field(default=False)
    rank: int = Field(default=0, ge=1, le=5)

    created_at: datetime = Field(default_factory=utc_now)

    timed_meal: Optional["TimedMeal"] = Relationship(back_populates="combo_options")
    meal_combo: Optional["MealCombo"] = Relationship()


# ── Plans ──────────────────────────────────────────────────────────────────

class WeekMealPlanBase(SQLModel):
    title: str = Field(max_length=255, index=True)
    start_date: date = Field(index=True)
    end_date: date = Field(index=True)
    status: PlanStatus = Field(default=PlanStatus.draft, index=True)


class WeekMealPlan(WeekMealPlanBase, table=True):
    __tablename__ = "week_meal_plan"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id", index=True)

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    day_plans: List["DayMealPlan"] = Relationship(back_populates="week_plan")


class DayMealPlanBase(SQLModel):
    plan_date: date = Field(index=True)
    note: Optional[str] = None


class DayMealPlan(DayMealPlanBase, table=True):
    __tablename__ = "day_meal_plan"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    week_plan_id: uuid.UUID = Field(foreign_key="week_meal_plan.id", index=True)

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    week_plan: Optional["WeekMealPlan"] = Relationship(back_populates="day_plans")
    timed_meals: List["TimedMeal"] = Relationship(back_populates="day_plan")


class LikedMeal(SQLModel, table=True):
    __tablename__ = "liked_meal"

    user_id: uuid.UUID = Field(foreign_key="users.id", primary_key=True)
    meal_id: uuid.UUID = Field(foreign_key="meal.id", primary_key=True)

    created_at: datetime = Field(default_factory=utc_now)

    user: Optional["User"] = Relationship()
    meal: Optional["Meal"] = Relationship()


# ── Meal plan settings ─────────────────────────────────────────────────────

class MealPlanSettingBase(SQLModel):
    name: str = Field(max_length=255, index=True)
    timed_meals_per_day: int = Field(ge=1, le=12)


class MealPlanSetting(MealPlanSettingBase, table=True):
    __tablename__ = "meal_plan_setting"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    created_for: uuid.UUID = Field(foreign_key="users.id", index=True)
    created_by: uuid.UUID = Field(foreign_key="users.id", index=True)
    appointment_id: Optional[uuid.UUID] = Field(default=None, foreign_key="appointments.id", index=True)
    active: bool = Field(default=False, nullable=False)

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    timed_meals: List["MealPlanSettingTimedMeal"] = Relationship(
        back_populates="meal_plan_setting"
    )


class MealPlanSettingTimedMealBase(SQLModel):
    name: str = Field(max_length=100)
    meal_time: MealTimeType = Field(index=True)

    calories_pct: float = Field(default=0, ge=0, le=100)
    protein_g_pct: float = Field(default=0, ge=0, le=100)
    carbs_g_pct: float = Field(default=0, ge=0, le=100)
    fat_g_pct: float = Field(default=0, ge=0, le=100)

    # Labels that guide meal selection (e.g., breakfast, high_protein). Stored as JSON.
    meal_labels: List[MealLabelName] = Field(default=[], sa_column=Column(JSON, nullable=False, default=[]))


class MealPlanSettingTimedMeal(MealPlanSettingTimedMealBase, table=True):
    __tablename__ = "meal_plan_setting_timed_meal"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    meal_plan_setting_id: uuid.UUID = Field(
        foreign_key="meal_plan_setting.id",
        index=True,
    )

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    meal_plan_setting: Optional["MealPlanSetting"] = Relationship(
        back_populates="timed_meals"
    )


# Re-export DTO schemas so `from app.modules.meal.models import X` keeps working.
# Imported last (after all tables/enums/bases are defined) to keep load order safe.
from .schemas import *  # noqa: E402,F401,F403
