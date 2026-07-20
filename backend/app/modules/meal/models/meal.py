from datetime import datetime, time, timezone
from enum import Enum
from typing import TYPE_CHECKING, List, Optional
import uuid

from sqlalchemy import JSON, Column, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel
from pgvector.sqlalchemy import Vector

# Shared vocabulary — also used by `meal_plan_setting/`. Defined in core so the two
# modules don't have to import each other. Re-exported here for back-compat.
from app.core.enums import MealTimeType, MealLabelName  # noqa: F401
# MeasureUnit lives in core/units.py with the rest of the unit vocabulary.
# ⚠️ Its member NAMES are the storage contract (DB holds "gram"/"milliliter").
from app.core.units import MeasureUnit  # noqa: F401

EMBEDDING_DIM = 1024


if TYPE_CHECKING:
    from app.modules.user.models import User


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ── Enums ──────────────────────────────────────────────────────────────────

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


# MealLabelName and MealTimeType now live in app.core.enums (imported above) —
# `meal_plan_setting/` needs them too, and defining them here would create a cycle.


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

    # Label names from FoodItemLabelName, stored as a JSONB string array.
    labels: List[str] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    )

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


# ── Meals ──────────────────────────────────────────────────────────────────

class MealBase(MacroFields, SQLModel):
    name: str = Field(index=True, max_length=255)
    description: Optional[str] = None
    instructions: Optional[str] = None
    image_url: Optional[str] = None

    servings: float = Field(default=1, gt=0)
    total_weight_g: Optional[float] = Field(default=None, gt=0)

    is_verified: bool = Field(default=True, index=True)

    # Extra nutrients (LLM-estimated) for health-aware filtering
    sodium_mg: float = Field(default=0, ge=0)
    fiber_g: float = Field(default=0, ge=0)
    sugar_g: float = Field(default=0, ge=0)
    # LLM-written free-text health context (the open-ended semantic layer; embedded, not an enum)
    ai_health_context: Optional[str] = None
    # Enrichment cache gate: hash of the meal's source text; re-enrich when it changes.
    enriched_hash: Optional[str] = None
    enriched_at: Optional[datetime] = None


class Meal(MealBase, table=True):
    __tablename__ = "meal"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    # Label names from MealLabelName, stored as a JSONB string array.
    labels: List[str] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    )

    # Ingredients, stored as a JSONB array of objects:
    #   {"food_item_id": "<uuid str>", "quantity": <float>, "unit": "gram|milliliter|piece|tbsp"}
    # food_item rows may be deleted independently — readers must tolerate missing ids.
    ingredients: List[dict] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    )

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    combo_items: List["MealComboItem"] = Relationship(
        back_populates="meal",
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
    status: PlanStatus = Field(default=PlanStatus.draft, index=True)


class WeekMealPlan(WeekMealPlanBase, table=True):
    """A user's recurring weekly meal plan — a Mon–Sun template, not a dated week.
    One per user (enforced by uq_week_meal_plan_user)."""
    __tablename__ = "week_meal_plan"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_week_meal_plan_user"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id", index=True)

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    day_plans: List["DayMealPlan"] = Relationship(back_populates="week_plan")


class DayMealPlanBase(SQLModel):
    # Weekday this day plan covers (Mon=0 … Sun=6), matching DailyGoal.days_of_week.
    day_of_week: int = Field(index=True, ge=0, le=6)
    note: Optional[str] = None


class DayMealPlan(DayMealPlanBase, table=True):
    __tablename__ = "day_meal_plan"
    __table_args__ = (
        UniqueConstraint("week_plan_id", "day_of_week", name="uq_day_meal_plan_week_dow"),
    )

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
# Moved to app.modules.meal_plan_setting.models (tables unchanged:
# `meal_plan_setting`, `meal_plan_setting_timed_meal`). Re-exported at the bottom
# of this file for back-compat; deleted in Phase 4.


# ── Meal embeddings (pgvector) ─────────────────────────────────────────────

class MealEmbedding(SQLModel, table=True):
    __tablename__ = "meal_embedding"

    meal_id: uuid.UUID = Field(foreign_key="meal.id", primary_key=True)
    text_hash: str = Field(index=True)
    model: str
    embedding: List[float] = Field(sa_column=Column(Vector(EMBEDDING_DIM)))
    updated_at: datetime = Field(default_factory=utc_now)


# Re-export the meal-plan-setting tables so `from app.modules.meal.models import X`
# keeps working. Safe in either import order: meal_plan_setting/models.py depends only
# on app.core.enums, never on this module.
from app.modules.meal_plan_setting.models import (  # noqa: E402,F401
    MealPlanSettingBase,
    MealPlanSetting,
    MealPlanSettingTimedMealBase,
    MealPlanSettingTimedMeal,
)
