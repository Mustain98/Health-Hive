"""Vocabulary shared across domain modules.

These enums are referenced by more than one module (e.g. `meal/` defines meals against
`MealTimeType`, and `meal_plan_setting/` slots them by the same type). Keeping them here
instead of in either module is what stops the two from importing each other.

Phase 2 adds the unit enums (`WeightUnit`, `DurationUnit`, …) alongside these.
"""
from enum import Enum


class MealTimeType(str, Enum):
    breakfast = "breakfast"
    lunch = "lunch"
    dinner = "dinner"
    snack = "snack"


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
