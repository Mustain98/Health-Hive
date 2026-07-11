"""Valid label vocabularies for food items and meals.

Source of truth: the enums in the MAIN backend —
backend/app/modules/meal/models.py (FoodItemLabelName, MealLabelName).
Labels are stored as JSONB string arrays on food_item.labels / meal.labels;
there are no label tables anymore. Keep these lists in sync with the enums.
"""

FOOD_ITEM_LABELS: list[str] = [
    "grain", "meat", "fish", "dairy", "vegetable", "fruit", "legume", "nut_seed",
    "oil_fat", "beverage", "spice", "sweetener",
    "halal", "vegetarian", "vegan",
    "egg", "gluten", "nuts", "shellfish", "soy",
    "high_protein", "high_fiber", "low_carb", "low_fat",
    "other",
]

MEAL_LABELS: list[str] = [
    "breakfast", "lunch", "dinner", "snack",
    "main_meal", "side_meal", "drink", "dessert",
    "halal", "vegetarian", "vegan",
    "high_protein", "low_carb", "gym_friendly",
    "other",
]
