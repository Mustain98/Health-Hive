"""
Seed script for meals and food items.
Run from inside /backend:
    python seed_meals.py

The script is idempotent – it only inserts rows that do not already exist
(matched by name / label-name).
"""

import sys
import os

# Make sure app package is importable when running from /backend
sys.path.insert(0, os.path.dirname(__file__))

from sqlmodel import Session, select
from app.core.database import engine
from app.models.meal_plan.food_item import (
    FoodItem,
    FoodItemLabel,
    FoodItemLabelLink,
    FoodItemLabelName,
    MeasureUnit,
)
from app.models.user import User  # noqa: F401 – needed to resolve ORM relationships (LikedMeal)
from app.models.meal_plan.plan import WeekMealPlan, DayMealPlan  # noqa: F401 – needed to resolve ORM relationships
from app.models.meal_plan.meal import (
    Meal,
    MealLabel,
    MealLabelLink,
    MealLabelName,
    MealFoodItem,
    MealCombo,
    MealComboItem,
    MealTimeType,
)


# ---------------------------------------------------------------------------
# 1.  FOOD ITEMS
# ---------------------------------------------------------------------------
# Nutrition values:
#   - gram / ml  → per 100 g / ml
#   - piece / tbsp → per 1 piece / tbsp
# ---------------------------------------------------------------------------

FOOD_ITEMS_DATA = [
    # ── Grains ──────────────────────────────────────────────────────
    {
        "name": "Cooked White Rice",
        "description": "Long-grain white rice, steamed. Commonly used as a base in lunches and dinners.",
        "nutrition_unit": MeasureUnit.gram,
        "calories": 130.0,
        "protein_g": 2.7,
        "carbs_g": 28.2,
        "fat_g": 0.3,
        "is_verified": True,
        "labels": [FoodItemLabelName.grain, FoodItemLabelName.halal, FoodItemLabelName.vegan],
    },
    {
        "name": "Whole Wheat Bread",
        "description": "Dense, fibre-rich bread made from 100 % whole wheat flour.",
        "nutrition_unit": MeasureUnit.piece,
        "weight_per_unit_g": 30.0,
        "calories": 69.0,
        "protein_g": 3.6,
        "carbs_g": 11.6,
        "fat_g": 1.1,
        "is_verified": True,
        "labels": [FoodItemLabelName.grain, FoodItemLabelName.high_fiber, FoodItemLabelName.vegan],
    },
    {
        "name": "Rolled Oats",
        "description": "Old-fashioned oats, dry. Rich in beta-glucan, great for breakfast porridge.",
        "nutrition_unit": MeasureUnit.gram,
        "calories": 389.0,
        "protein_g": 16.9,
        "carbs_g": 66.3,
        "fat_g": 6.9,
        "is_verified": True,
        "labels": [FoodItemLabelName.grain, FoodItemLabelName.high_fiber, FoodItemLabelName.vegan],
    },
    {
        "name": "Cooked Quinoa",
        "description": "Cooked quinoa – a complete protein grain, gluten-free.",
        "nutrition_unit": MeasureUnit.gram,
        "calories": 120.0,
        "protein_g": 4.4,
        "carbs_g": 21.3,
        "fat_g": 1.9,
        "is_verified": True,
        "labels": [
            FoodItemLabelName.grain,
            FoodItemLabelName.high_protein,
            FoodItemLabelName.vegan,
            FoodItemLabelName.halal,
        ],
    },
    # ── Meat ────────────────────────────────────────────────────────
    {
        "name": "Grilled Chicken Breast",
        "description": "Skinless, boneless chicken breast, grilled. Lean and high in protein.",
        "nutrition_unit": MeasureUnit.gram,
        "calories": 165.0,
        "protein_g": 31.0,
        "carbs_g": 0.0,
        "fat_g": 3.6,
        "is_verified": True,
        "labels": [
            FoodItemLabelName.meat,
            FoodItemLabelName.halal,
            FoodItemLabelName.high_protein,
            FoodItemLabelName.low_fat,
            FoodItemLabelName.low_carb,
        ],
    },
    {
        "name": "Lean Ground Beef (90/10)",
        "description": "90 % lean, 10 % fat ground beef, cooked. Good source of iron and zinc.",
        "nutrition_unit": MeasureUnit.gram,
        "calories": 215.0,
        "protein_g": 26.1,
        "carbs_g": 0.0,
        "fat_g": 11.7,
        "is_verified": True,
        "labels": [FoodItemLabelName.meat, FoodItemLabelName.halal, FoodItemLabelName.high_protein],
    },
    {
        "name": "Turkey Breast (Sliced)",
        "description": "Deli-style sliced turkey breast, low-fat. High protein snack or sandwich filler.",
        "nutrition_unit": MeasureUnit.gram,
        "calories": 135.0,
        "protein_g": 29.9,
        "carbs_g": 0.0,
        "fat_g": 1.0,
        "is_verified": True,
        "labels": [
            FoodItemLabelName.meat,
            FoodItemLabelName.halal,
            FoodItemLabelName.high_protein,
            FoodItemLabelName.low_fat,
        ],
    },
    # ── Fish / Seafood ───────────────────────────────────────────────
    {
        "name": "Atlantic Salmon Fillet",
        "description": "Pan-seared Atlantic salmon. Rich in omega-3 fatty acids and vitamin D.",
        "nutrition_unit": MeasureUnit.gram,
        "calories": 208.0,
        "protein_g": 20.0,
        "carbs_g": 0.0,
        "fat_g": 13.4,
        "is_verified": True,
        "labels": [FoodItemLabelName.fish, FoodItemLabelName.halal, FoodItemLabelName.high_protein],
    },
    {
        "name": "Canned Tuna in Water",
        "description": "Chunk light tuna packed in water, drained. Convenient lean protein source.",
        "nutrition_unit": MeasureUnit.gram,
        "calories": 109.0,
        "protein_g": 25.5,
        "carbs_g": 0.0,
        "fat_g": 0.5,
        "is_verified": True,
        "labels": [
            FoodItemLabelName.fish,
            FoodItemLabelName.halal,
            FoodItemLabelName.high_protein,
            FoodItemLabelName.low_fat,
            FoodItemLabelName.low_carb,
        ],
    },
    # ── Dairy ────────────────────────────────────────────────────────
    {
        "name": "Greek Yogurt (Plain, 0% Fat)",
        "description": "Strained Greek yogurt, non-fat. Excellent probiotic and protein source.",
        "nutrition_unit": MeasureUnit.gram,
        "calories": 59.0,
        "protein_g": 10.0,
        "carbs_g": 3.6,
        "fat_g": 0.4,
        "is_verified": True,
        "labels": [
            FoodItemLabelName.dairy,
            FoodItemLabelName.high_protein,
            FoodItemLabelName.vegetarian,
            FoodItemLabelName.low_fat,
        ],
    },
    {
        "name": "Whole Milk",
        "description": "Full-fat cow's milk (3.25 % fat). Rich in calcium and vitamins A and D.",
        "nutrition_unit": MeasureUnit.milliliter,
        "calories": 61.0,
        "protein_g": 3.2,
        "carbs_g": 4.8,
        "fat_g": 3.3,
        "is_verified": True,
        "labels": [FoodItemLabelName.dairy, FoodItemLabelName.halal, FoodItemLabelName.vegetarian],
    },
    {
        "name": "Cheddar Cheese",
        "description": "Aged cheddar cheese. Good source of calcium and fat-soluble vitamins.",
        "nutrition_unit": MeasureUnit.gram,
        "calories": 403.0,
        "protein_g": 25.0,
        "carbs_g": 1.3,
        "fat_g": 33.1,
        "is_verified": True,
        "labels": [
            FoodItemLabelName.dairy,
            FoodItemLabelName.vegetarian,
            FoodItemLabelName.low_carb,
        ],
    },
    # ── Egg ─────────────────────────────────────────────────────────
    {
        "name": "Whole Egg",
        "description": "Large chicken egg (raw weight ~50 g). Complete protein with all essential amino acids.",
        "nutrition_unit": MeasureUnit.piece,
        "weight_per_unit_g": 50.0,
        "calories": 72.0,
        "protein_g": 6.3,
        "carbs_g": 0.4,
        "fat_g": 4.8,
        "is_verified": True,
        "labels": [
            FoodItemLabelName.egg,
            FoodItemLabelName.halal,
            FoodItemLabelName.vegetarian,
            FoodItemLabelName.high_protein,
        ],
    },
    # ── Vegetables ───────────────────────────────────────────────────
    {
        "name": "Broccoli Florets",
        "description": "Fresh or lightly steamed broccoli. High in vitamin C, folate, and fibre.",
        "nutrition_unit": MeasureUnit.gram,
        "calories": 34.0,
        "protein_g": 2.8,
        "carbs_g": 6.6,
        "fat_g": 0.4,
        "is_verified": True,
        "labels": [
            FoodItemLabelName.vegetable,
            FoodItemLabelName.vegan,
            FoodItemLabelName.halal,
            FoodItemLabelName.high_fiber,
            FoodItemLabelName.low_fat,
            FoodItemLabelName.low_carb,
        ],
    },
    {
        "name": "Baby Spinach",
        "description": "Fresh baby spinach leaves. Very low calorie, rich in iron, potassium, and vitamin K.",
        "nutrition_unit": MeasureUnit.gram,
        "calories": 23.0,
        "protein_g": 2.9,
        "carbs_g": 3.6,
        "fat_g": 0.4,
        "is_verified": True,
        "labels": [
            FoodItemLabelName.vegetable,
            FoodItemLabelName.vegan,
            FoodItemLabelName.halal,
            FoodItemLabelName.high_fiber,
            FoodItemLabelName.low_fat,
        ],
    },
    {
        "name": "Cherry Tomatoes",
        "description": "Red cherry tomatoes. Rich in lycopene and vitamin C.",
        "nutrition_unit": MeasureUnit.gram,
        "calories": 18.0,
        "protein_g": 0.9,
        "carbs_g": 3.9,
        "fat_g": 0.2,
        "is_verified": True,
        "labels": [
            FoodItemLabelName.vegetable,
            FoodItemLabelName.vegan,
            FoodItemLabelName.halal,
            FoodItemLabelName.low_fat,
        ],
    },
    {
        "name": "Sweet Potato",
        "description": "Baked sweet potato flesh, no skin. High in beta-carotene and potassium.",
        "nutrition_unit": MeasureUnit.gram,
        "calories": 90.0,
        "protein_g": 2.0,
        "carbs_g": 20.7,
        "fat_g": 0.1,
        "is_verified": True,
        "labels": [
            FoodItemLabelName.vegetable,
            FoodItemLabelName.vegan,
            FoodItemLabelName.halal,
            FoodItemLabelName.high_fiber,
        ],
    },
    {
        "name": "Red Bell Pepper",
        "description": "Raw red bell pepper. Exceptionally high in vitamin C and antioxidants.",
        "nutrition_unit": MeasureUnit.gram,
        "calories": 31.0,
        "protein_g": 1.0,
        "carbs_g": 6.0,
        "fat_g": 0.3,
        "is_verified": True,
        "labels": [
            FoodItemLabelName.vegetable,
            FoodItemLabelName.vegan,
            FoodItemLabelName.halal,
            FoodItemLabelName.low_fat,
        ],
    },
    # ── Fruit ────────────────────────────────────────────────────────
    {
        "name": "Banana",
        "description": "Medium ripe banana (~118 g). Good source of potassium and quick carbohydrate energy.",
        "nutrition_unit": MeasureUnit.piece,
        "weight_per_unit_g": 118.0,
        "calories": 105.0,
        "protein_g": 1.3,
        "carbs_g": 27.0,
        "fat_g": 0.4,
        "is_verified": True,
        "labels": [FoodItemLabelName.fruit, FoodItemLabelName.vegan, FoodItemLabelName.halal],
    },
    {
        "name": "Blueberries",
        "description": "Fresh wild blueberries. Rich in anthocyanins, vitamin C, and manganese.",
        "nutrition_unit": MeasureUnit.gram,
        "calories": 57.0,
        "protein_g": 0.7,
        "carbs_g": 14.5,
        "fat_g": 0.3,
        "is_verified": True,
        "labels": [FoodItemLabelName.fruit, FoodItemLabelName.vegan, FoodItemLabelName.halal],
    },
    {
        "name": "Apple",
        "description": "Medium red apple with skin (~182 g). Good source of fibre and vitamin C.",
        "nutrition_unit": MeasureUnit.piece,
        "weight_per_unit_g": 182.0,
        "calories": 95.0,
        "protein_g": 0.5,
        "carbs_g": 25.1,
        "fat_g": 0.3,
        "is_verified": True,
        "labels": [
            FoodItemLabelName.fruit,
            FoodItemLabelName.vegan,
            FoodItemLabelName.high_fiber,
            FoodItemLabelName.halal,
        ],
    },
    # ── Legumes ──────────────────────────────────────────────────────
    {
        "name": "Cooked Chickpeas",
        "description": "Boiled chickpeas (garbanzo beans). Great plant protein and fibre source.",
        "nutrition_unit": MeasureUnit.gram,
        "calories": 164.0,
        "protein_g": 8.9,
        "carbs_g": 27.4,
        "fat_g": 2.6,
        "is_verified": True,
        "labels": [
            FoodItemLabelName.legume,
            FoodItemLabelName.vegan,
            FoodItemLabelName.halal,
            FoodItemLabelName.high_fiber,
            FoodItemLabelName.high_protein,
        ],
    },
    {
        "name": "Black Beans (Cooked)",
        "description": "Boiled black beans. Excellent plant-based protein and fibre.",
        "nutrition_unit": MeasureUnit.gram,
        "calories": 132.0,
        "protein_g": 8.9,
        "carbs_g": 23.7,
        "fat_g": 0.5,
        "is_verified": True,
        "labels": [
            FoodItemLabelName.legume,
            FoodItemLabelName.vegan,
            FoodItemLabelName.halal,
            FoodItemLabelName.high_fiber,
            FoodItemLabelName.high_protein,
        ],
    },
    {
        "name": "Red Lentils (Cooked)",
        "description": "Cooked red lentils. Rich in folate, iron, and plant protein.",
        "nutrition_unit": MeasureUnit.gram,
        "calories": 116.0,
        "protein_g": 9.0,
        "carbs_g": 20.1,
        "fat_g": 0.4,
        "is_verified": True,
        "labels": [
            FoodItemLabelName.legume,
            FoodItemLabelName.vegan,
            FoodItemLabelName.halal,
            FoodItemLabelName.high_protein,
            FoodItemLabelName.high_fiber,
        ],
    },
    # ── Nuts & Seeds ─────────────────────────────────────────────────
    {
        "name": "Almonds (Raw)",
        "description": "Raw whole almonds. Rich in vitamin E, magnesium, and healthy monounsaturated fat.",
        "nutrition_unit": MeasureUnit.gram,
        "calories": 579.0,
        "protein_g": 21.2,
        "carbs_g": 21.6,
        "fat_g": 49.9,
        "is_verified": True,
        "labels": [
            FoodItemLabelName.nut_seed,
            FoodItemLabelName.nuts,
            FoodItemLabelName.vegan,
            FoodItemLabelName.halal,
            FoodItemLabelName.high_protein,
            FoodItemLabelName.high_fiber,
        ],
    },
    {
        "name": "Chia Seeds",
        "description": "Dried chia seeds. Very high in omega-3 ALA, fibre, and calcium.",
        "nutrition_unit": MeasureUnit.gram,
        "calories": 486.0,
        "protein_g": 16.5,
        "carbs_g": 42.1,
        "fat_g": 30.7,
        "is_verified": True,
        "labels": [
            FoodItemLabelName.nut_seed,
            FoodItemLabelName.vegan,
            FoodItemLabelName.halal,
            FoodItemLabelName.high_fiber,
        ],
    },
    # ── Oils & Fats ──────────────────────────────────────────────────
    {
        "name": "Extra Virgin Olive Oil",
        "description": "Cold-pressed EVOO. Rich in oleocanthal and monounsaturated fatty acids.",
        "nutrition_unit": MeasureUnit.tbsp,
        "weight_per_unit_g": 13.5,
        "calories": 119.0,
        "protein_g": 0.0,
        "carbs_g": 0.0,
        "fat_g": 13.5,
        "is_verified": True,
        "labels": [
            FoodItemLabelName.oil_fat,
            FoodItemLabelName.vegan,
            FoodItemLabelName.halal,
            FoodItemLabelName.low_carb,
        ],
    },
    # ── Beverages ────────────────────────────────────────────────────
    {
        "name": "Skimmed Milk",
        "description": "Fat-free cow's milk. High in calcium and protein with very low fat.",
        "nutrition_unit": MeasureUnit.milliliter,
        "calories": 34.0,
        "protein_g": 3.4,
        "carbs_g": 5.0,
        "fat_g": 0.1,
        "is_verified": True,
        "labels": [
            FoodItemLabelName.beverage,
            FoodItemLabelName.dairy,
            FoodItemLabelName.halal,
            FoodItemLabelName.vegetarian,
            FoodItemLabelName.low_fat,
        ],
    },
    # ── Sweetener ────────────────────────────────────────────────────
    {
        "name": "Honey",
        "description": "Raw natural honey. Natural sweetener with antimicrobial properties.",
        "nutrition_unit": MeasureUnit.tbsp,
        "weight_per_unit_g": 21.0,
        "calories": 64.0,
        "protein_g": 0.1,
        "carbs_g": 17.3,
        "fat_g": 0.0,
        "is_verified": True,
        "labels": [
            FoodItemLabelName.sweetener,
            FoodItemLabelName.halal,
            FoodItemLabelName.vegetarian,
        ],
    },
]


# ---------------------------------------------------------------------------
# 2.  FOOD-ITEM LABELS  (ensure all used labels pre-exist)
# ---------------------------------------------------------------------------

ALL_LABEL_NAMES_USED = set()
for fi in FOOD_ITEMS_DATA:
    for lbl in fi["labels"]:
        ALL_LABEL_NAMES_USED.add(lbl)

LABEL_DESCRIPTIONS = {
    FoodItemLabelName.grain: "Starchy grain-based foods such as rice, bread, oats, and quinoa.",
    FoodItemLabelName.meat: "Animal protein from red or white meat sources (non-seafood).",
    FoodItemLabelName.fish: "Fish and other seafood.",
    FoodItemLabelName.dairy: "Products derived from animal milk including yogurt, cheese, and milk.",
    FoodItemLabelName.vegetable: "Edible plant matter excluding grains and legumes.",
    FoodItemLabelName.fruit: "Sweet or savoury edible plant fruits.",
    FoodItemLabelName.legume: "Beans, lentils, peas, and other pod-bearing plants.",
    FoodItemLabelName.nut_seed: "Tree nuts and seeds.",
    FoodItemLabelName.oil_fat: "Cooking oils and concentrated fat sources.",
    FoodItemLabelName.beverage: "Drinkable liquids including milk and plant-based drinks.",
    FoodItemLabelName.spice: "Herbs, spices, and condiments used for flavouring.",
    FoodItemLabelName.sweetener: "Natural or refined sweetening agents.",
    FoodItemLabelName.halal: "Permissible according to Islamic dietary law.",
    FoodItemLabelName.vegetarian: "Contains no meat or seafood.",
    FoodItemLabelName.vegan: "Free of all animal products.",
    FoodItemLabelName.egg: "Contains eggs or is an egg product.",
    FoodItemLabelName.gluten: "Contains gluten from wheat, barley, or rye.",
    FoodItemLabelName.nuts: "Contains tree nuts – allergen label.",
    FoodItemLabelName.shellfish: "Contains shellfish – allergen label.",
    FoodItemLabelName.soy: "Contains soy – allergen label.",
    FoodItemLabelName.high_protein: "Provides ≥ 20 g protein per standard serving.",
    FoodItemLabelName.high_fiber: "Provides ≥ 5 g dietary fibre per standard serving.",
    FoodItemLabelName.low_carb: "Contains ≤ 5 g net carbs per serving.",
    FoodItemLabelName.low_fat: "Contains ≤ 3 g total fat per serving.",
    FoodItemLabelName.other: "Miscellaneous items not covered by other labels.",
}


# ---------------------------------------------------------------------------
# 3.  MEALS  (diverse types – breakfast, lunch, dinner, snack, etc.)
# ---------------------------------------------------------------------------

MEALS_DATA = [
    # ── BREAKFAST ────────────────────────────────────────────────
    {
        "name": "Classic Oatmeal Bowl",
        "description": (
            "Creamy oat porridge topped with banana slices, blueberries, "
            "honey, and a sprinkle of chia seeds. A fibre-rich, energising breakfast."
        ),
        "instructions": (
            "1. Cook rolled oats in whole milk (1:2 ratio) over medium heat for 5 min, stirring often.\n"
            "2. Pour into a bowl. Slice banana on top.\n"
            "3. Add blueberries, drizzle honey, sprinkle chia seeds. Serve hot."
        ),
        "servings": 1.0,
        "total_weight_g": 420.0,
        "calories": 485.0,
        "protein_g": 16.5,
        "carbs_g": 85.0,
        "fat_g": 10.2,
        "is_verified": True,
        "labels": [MealLabelName.breakfast, MealLabelName.vegetarian, MealLabelName.halal],
        "ingredients": [
            # (food_item_name, quantity, unit)
            ("Rolled Oats", 80.0, MeasureUnit.gram),
            ("Whole Milk", 200.0, MeasureUnit.milliliter),
            ("Banana", 1.0, MeasureUnit.piece),
            ("Blueberries", 60.0, MeasureUnit.gram),
            ("Honey", 1.0, MeasureUnit.tbsp),
            ("Chia Seeds", 10.0, MeasureUnit.gram),
        ],
    },
    {
        "name": "Veggie Egg Scramble",
        "description": (
            "Fluffy scrambled eggs with sautéed baby spinach, cherry tomatoes, "
            "and red bell pepper. Served on a slice of whole wheat toast."
        ),
        "instructions": (
            "1. Whisk 3 eggs with a pinch of salt.\n"
            "2. Sauté spinach, cherry tomatoes, and red bell pepper in olive oil for 2 min.\n"
            "3. Add eggs, scramble gently over low-medium heat until just set.\n"
            "4. Serve on toasted whole wheat bread."
        ),
        "servings": 1.0,
        "total_weight_g": 360.0,
        "calories": 395.0,
        "protein_g": 27.8,
        "carbs_g": 22.0,
        "fat_g": 20.5,
        "is_verified": True,
        "labels": [
            MealLabelName.breakfast,
            MealLabelName.vegetarian,
            MealLabelName.halal,
            MealLabelName.high_protein,
        ],
        "ingredients": [
            ("Whole Egg", 3.0, MeasureUnit.piece),
            ("Baby Spinach", 50.0, MeasureUnit.gram),
            ("Cherry Tomatoes", 80.0, MeasureUnit.gram),
            ("Red Bell Pepper", 60.0, MeasureUnit.gram),
            ("Extra Virgin Olive Oil", 1.0, MeasureUnit.tbsp),
            ("Whole Wheat Bread", 1.0, MeasureUnit.piece),
        ],
    },
    {
        "name": "Greek Yogurt Parfait",
        "description": (
            "Layered Greek yogurt with blueberries, apple chunks, honey, "
            "and crushed almonds. High-protein, no-cook breakfast or snack."
        ),
        "instructions": (
            "1. Spoon Greek yogurt into a glass.\n"
            "2. Add a layer of blueberries, then apple chunks.\n"
            "3. Top with crushed almonds and drizzle honey."
        ),
        "servings": 1.0,
        "total_weight_g": 310.0,
        "calories": 380.0,
        "protein_g": 22.0,
        "carbs_g": 45.0,
        "fat_g": 11.0,
        "is_verified": True,
        "labels": [
            MealLabelName.breakfast,
            MealLabelName.snack,
            MealLabelName.vegetarian,
            MealLabelName.halal,
            MealLabelName.high_protein,
        ],
        "ingredients": [
            ("Greek Yogurt (Plain, 0% Fat)", 200.0, MeasureUnit.gram),
            ("Blueberries", 60.0, MeasureUnit.gram),
            ("Apple", 0.5, MeasureUnit.piece),
            ("Honey", 1.0, MeasureUnit.tbsp),
            ("Almonds (Raw)", 20.0, MeasureUnit.gram),
        ],
    },
    # ── LUNCH ────────────────────────────────────────────────────
    {
        "name": "Grilled Chicken Rice Bowl",
        "description": (
            "Tender grilled chicken breast served over steamed white rice with "
            "a side of broccoli and cherry tomatoes. A classic balanced meal."
        ),
        "instructions": (
            "1. Season chicken breast with salt, pepper, and paprika.\n"
            "2. Grill on a hot pan with olive oil for 6–7 min per side.\n"
            "3. Steam broccoli for 4 min.\n"
            "4. Serve chicken sliced over rice, with broccoli and cherry tomatoes on the side."
        ),
        "servings": 1.0,
        "total_weight_g": 520.0,
        "calories": 540.0,
        "protein_g": 48.0,
        "carbs_g": 55.0,
        "fat_g": 10.0,
        "is_verified": True,
        "labels": [
            MealLabelName.lunch,
            MealLabelName.main_meal,
            MealLabelName.halal,
            MealLabelName.high_protein,
            MealLabelName.gym_friendly,
        ],
        "ingredients": [
            ("Grilled Chicken Breast", 150.0, MeasureUnit.gram),
            ("Cooked White Rice", 200.0, MeasureUnit.gram),
            ("Broccoli Florets", 100.0, MeasureUnit.gram),
            ("Cherry Tomatoes", 60.0, MeasureUnit.gram),
            ("Extra Virgin Olive Oil", 1.0, MeasureUnit.tbsp),
        ],
    },
    {
        "name": "Tuna & Chickpea Salad",
        "description": (
            "A protein-packed salad with canned tuna, chickpeas, baby spinach, "
            "red bell pepper, and cherry tomatoes dressed with olive oil."
        ),
        "instructions": (
            "1. Drain tuna and chickpeas.\n"
            "2. Combine all vegetables in a large bowl.\n"
            "3. Add tuna and chickpeas, drizzle with olive oil, season with salt and lemon."
        ),
        "servings": 1.0,
        "total_weight_g": 420.0,
        "calories": 430.0,
        "protein_g": 42.0,
        "carbs_g": 30.0,
        "fat_g": 12.0,
        "is_verified": True,
        "labels": [
            MealLabelName.lunch,
            MealLabelName.main_meal,
            MealLabelName.halal,
            MealLabelName.high_protein,
            MealLabelName.low_carb,
        ],
        "ingredients": [
            ("Canned Tuna in Water", 120.0, MeasureUnit.gram),
            ("Cooked Chickpeas", 100.0, MeasureUnit.gram),
            ("Baby Spinach", 60.0, MeasureUnit.gram),
            ("Red Bell Pepper", 60.0, MeasureUnit.gram),
            ("Cherry Tomatoes", 60.0, MeasureUnit.gram),
            ("Extra Virgin Olive Oil", 1.0, MeasureUnit.tbsp),
        ],
    },
    {
        "name": "Lentil & Sweet Potato Soup",
        "description": (
            "Hearty vegan soup made with red lentils, sweet potato, spinach, and warm spices. "
            "Filling and high in plant protein and fibre."
        ),
        "instructions": (
            "1. Sauté diced sweet potato in olive oil for 3 min.\n"
            "2. Add red lentils and 600 ml water or vegetable stock, simmer 20 min.\n"
            "3. Stir in spinach, season with cumin, turmeric, salt. Serve hot."
        ),
        "servings": 2.0,
        "total_weight_g": 700.0,
        "calories": 480.0,
        "protein_g": 22.0,
        "carbs_g": 82.0,
        "fat_g": 8.0,
        "is_verified": True,
        "labels": [
            MealLabelName.lunch,
            MealLabelName.dinner,
            MealLabelName.main_meal,
            MealLabelName.vegan,
            MealLabelName.halal,
            MealLabelName.high_protein,
        ],
        "ingredients": [
            ("Red Lentils (Cooked)", 200.0, MeasureUnit.gram),
            ("Sweet Potato", 200.0, MeasureUnit.gram),
            ("Baby Spinach", 60.0, MeasureUnit.gram),
            ("Extra Virgin Olive Oil", 1.0, MeasureUnit.tbsp),
        ],
    },
    {
        "name": "Quinoa & Black Bean Power Bowl",
        "description": (
            "A plant-based power bowl featuring cooked quinoa, black beans, "
            "roasted sweet potato, cherry tomatoes, and spinach."
        ),
        "instructions": (
            "1. Roast sweet potato cubes at 200 °C for 20 min with olive oil.\n"
            "2. Assemble bowl: quinoa base, then black beans, sweet potato, spinach, tomatoes.\n"
            "3. Dress with olive oil and lime juice."
        ),
        "servings": 1.0,
        "total_weight_g": 480.0,
        "calories": 520.0,
        "protein_g": 22.0,
        "carbs_g": 82.0,
        "fat_g": 10.0,
        "is_verified": True,
        "labels": [
            MealLabelName.lunch,
            MealLabelName.main_meal,
            MealLabelName.vegan,
            MealLabelName.halal,
            MealLabelName.high_protein,
        ],
        "ingredients": [
            ("Cooked Quinoa", 150.0, MeasureUnit.gram),
            ("Black Beans (Cooked)", 120.0, MeasureUnit.gram),
            ("Sweet Potato", 100.0, MeasureUnit.gram),
            ("Cherry Tomatoes", 60.0, MeasureUnit.gram),
            ("Baby Spinach", 50.0, MeasureUnit.gram),
            ("Extra Virgin Olive Oil", 1.0, MeasureUnit.tbsp),
        ],
    },
    # ── DINNER ───────────────────────────────────────────────────
    {
        "name": "Beef & Vegetable Stir-Fry with Rice",
        "description": (
            "Lean ground beef stir-fried with broccoli and red bell pepper, "
            "served over steamed white rice. Quick, balanced dinner."
        ),
        "instructions": (
            "1. Brown ground beef in a hot pan, drain excess fat.\n"
            "2. Add broccoli and red bell pepper, stir-fry for 4 min.\n"
            "3. Season with soy sauce, garlic, and ginger.\n"
            "4. Serve over steamed rice."
        ),
        "servings": 1.0,
        "total_weight_g": 500.0,
        "calories": 610.0,
        "protein_g": 40.0,
        "carbs_g": 58.0,
        "fat_g": 18.0,
        "is_verified": True,
        "labels": [
            MealLabelName.dinner,
            MealLabelName.main_meal,
            MealLabelName.halal,
            MealLabelName.high_protein,
        ],
        "ingredients": [
            ("Lean Ground Beef (90/10)", 120.0, MeasureUnit.gram),
            ("Cooked White Rice", 200.0, MeasureUnit.gram),
            ("Broccoli Florets", 100.0, MeasureUnit.gram),
            ("Red Bell Pepper", 80.0, MeasureUnit.gram),
            ("Extra Virgin Olive Oil", 0.5, MeasureUnit.tbsp),
        ],
    },
    {
        "name": "Baked Salmon with Quinoa & Broccoli",
        "description": (
            "Oven-baked Atlantic salmon fillet with a quinoa pilaf and steamed broccoli. "
            "Omega-3 rich, complete protein dinner."
        ),
        "instructions": (
            "1. Preheat oven to 200 °C. Season salmon with olive oil, lemon, dill, salt & pepper.\n"
            "2. Bake salmon for 14–16 min until flaky.\n"
            "3. Steam broccoli 4 min.\n"
            "4. Serve salmon over quinoa with broccoli on the side."
        ),
        "servings": 1.0,
        "total_weight_g": 450.0,
        "calories": 560.0,
        "protein_g": 45.0,
        "carbs_g": 35.0,
        "fat_g": 22.0,
        "is_verified": True,
        "labels": [
            MealLabelName.dinner,
            MealLabelName.main_meal,
            MealLabelName.halal,
            MealLabelName.high_protein,
            MealLabelName.gym_friendly,
        ],
        "ingredients": [
            ("Atlantic Salmon Fillet", 150.0, MeasureUnit.gram),
            ("Cooked Quinoa", 150.0, MeasureUnit.gram),
            ("Broccoli Florets", 120.0, MeasureUnit.gram),
            ("Extra Virgin Olive Oil", 1.0, MeasureUnit.tbsp),
        ],
    },
    {
        "name": "Turkey & Sweet Potato Bake",
        "description": (
            "Lean turkey breast strips baked with sweet potato wedges and bell pepper. "
            "High-protein, low-fat wholesome dinner."
        ),
        "instructions": (
            "1. Toss sweet potato wedges and bell pepper with olive oil, season well.\n"
            "2. Roast at 200 °C for 20 min.\n"
            "3. Add turkey strips, return to oven for 15 min until cooked through.\n"
            "4. Rest 5 min before serving."
        ),
        "servings": 1.0,
        "total_weight_g": 430.0,
        "calories": 480.0,
        "protein_g": 44.0,
        "carbs_g": 42.0,
        "fat_g": 10.0,
        "is_verified": True,
        "labels": [
            MealLabelName.dinner,
            MealLabelName.main_meal,
            MealLabelName.halal,
            MealLabelName.high_protein,
            MealLabelName.low_carb,
        ],
        "ingredients": [
            ("Turkey Breast (Sliced)", 150.0, MeasureUnit.gram),
            ("Sweet Potato", 200.0, MeasureUnit.gram),
            ("Red Bell Pepper", 80.0, MeasureUnit.gram),
            ("Extra Virgin Olive Oil", 1.0, MeasureUnit.tbsp),
        ],
    },
    # ── SNACK ────────────────────────────────────────────────────
    {
        "name": "Almond & Fruit Trail Mix",
        "description": (
            "Quick no-prep snack of raw almonds, blueberries, and apple slices. "
            "Great for on-the-go energy and micronutrients."
        ),
        "instructions": (
            "1. Measure almonds, blueberries, and slice half an apple into bite pieces.\n"
            "2. Combine in a small bowl or snack bag. Enjoy immediately."
        ),
        "servings": 1.0,
        "total_weight_g": 170.0,
        "calories": 290.0,
        "protein_g": 8.0,
        "carbs_g": 32.0,
        "fat_g": 16.0,
        "is_verified": True,
        "labels": [
            MealLabelName.snack,
            MealLabelName.vegan,
            MealLabelName.halal,
        ],
        "ingredients": [
            ("Almonds (Raw)", 30.0, MeasureUnit.gram),
            ("Blueberries", 60.0, MeasureUnit.gram),
            ("Apple", 0.5, MeasureUnit.piece),
        ],
    },
    {
        "name": "High-Protein Milk & Banana Shake",
        "description": (
            "Simple 3-ingredient shake: skimmed milk, banana, and Greek yogurt. "
            "Post-workout recovery or afternoon snack."
        ),
        "instructions": (
            "1. Blend skimmed milk, banana, and Greek yogurt until smooth.\n"
            "2. Pour into a tall glass and serve chilled."
        ),
        "servings": 1.0,
        "total_weight_g": 420.0,
        "calories": 330.0,
        "protein_g": 22.0,
        "carbs_g": 52.0,
        "fat_g": 2.5,
        "is_verified": True,
        "labels": [
            MealLabelName.snack,
            MealLabelName.drink,
            MealLabelName.vegetarian,
            MealLabelName.halal,
            MealLabelName.high_protein,
        ],
        "ingredients": [
            ("Skimmed Milk", 300.0, MeasureUnit.milliliter),
            ("Banana", 1.0, MeasureUnit.piece),
            ("Greek Yogurt (Plain, 0% Fat)", 100.0, MeasureUnit.gram),
        ],
    },
    # ── DESSERT ──────────────────────────────────────────────────
    {
        "name": "Chia Seed Pudding with Blueberries",
        "description": (
            "Overnight chia pudding made with whole milk and topped with fresh blueberries "
            "and a drizzle of honey. Rich in omega-3 and antioxidants."
        ),
        "instructions": (
            "1. Stir chia seeds into whole milk, add honey. Mix well.\n"
            "2. Refrigerate for at least 4 hours or overnight.\n"
            "3. Top with fresh blueberries before serving."
        ),
        "servings": 1.0,
        "total_weight_g": 320.0,
        "calories": 310.0,
        "protein_g": 10.0,
        "carbs_g": 38.0,
        "fat_g": 12.0,
        "is_verified": True,
        "labels": [
            MealLabelName.dessert,
            MealLabelName.snack,
            MealLabelName.vegetarian,
            MealLabelName.halal,
        ],
        "ingredients": [
            ("Chia Seeds", 30.0, MeasureUnit.gram),
            ("Whole Milk", 250.0, MeasureUnit.milliliter),
            ("Honey", 1.0, MeasureUnit.tbsp),
            ("Blueberries", 60.0, MeasureUnit.gram),
        ],
    },
    # ── SIDE ─────────────────────────────────────────────────────
    {
        "name": "Steamed Broccoli with Olive Oil",
        "description": (
            "Simple steamed broccoli florets finished with a drizzle of extra virgin olive oil "
            "and a squeeze of lemon. Versatile low-calorie side dish."
        ),
        "instructions": (
            "1. Steam broccoli florets for 4–5 min until bright green and tender-crisp.\n"
            "2. Transfer to a bowl, drizzle with olive oil, season with salt and lemon juice."
        ),
        "servings": 1.0,
        "total_weight_g": 200.0,
        "calories": 150.0,
        "protein_g": 5.6,
        "carbs_g": 13.2,
        "fat_g": 8.0,
        "is_verified": True,
        "labels": [
            MealLabelName.side_meal,
            MealLabelName.vegan,
            MealLabelName.halal,
            MealLabelName.low_carb,
        ],
        "ingredients": [
            ("Broccoli Florets", 180.0, MeasureUnit.gram),
            ("Extra Virgin Olive Oil", 1.0, MeasureUnit.tbsp),
        ],
    },
]


# ---------------------------------------------------------------------------
# 4.  MEAL LABELS  (ensure all used labels pre-exist in meal_label table)
# ---------------------------------------------------------------------------

ALL_MEAL_LABEL_NAMES_USED = set()
for m in MEALS_DATA:
    for lbl in m["labels"]:
        ALL_MEAL_LABEL_NAMES_USED.add(lbl)

MEAL_LABEL_DESCRIPTIONS = {
    MealLabelName.breakfast: "Morning meal suitable for breaking overnight fast.",
    MealLabelName.lunch: "Mid-day main meal.",
    MealLabelName.dinner: "Evening main meal.",
    MealLabelName.snack: "Small meal or bite between main meals.",
    MealLabelName.main_meal: "Primary, calorie-dense meal of the day.",
    MealLabelName.side_meal: "Accompaniment or supplement to a main meal.",
    MealLabelName.drink: "Beverage or drinkable item.",
    MealLabelName.dessert: "Sweet course served after the main meal.",
    MealLabelName.halal: "Compliant with Islamic dietary law.",
    MealLabelName.vegetarian: "Contains no meat or seafood.",
    MealLabelName.vegan: "Free of all animal products.",
    MealLabelName.high_protein: "Provides ≥ 30 g of protein per serving.",
    MealLabelName.low_carb: "Contains ≤ 20 g net carbs per serving.",
    MealLabelName.gym_friendly: "Suitable for athletes and gym-goers; balanced macros.",
    MealLabelName.other: "Miscellaneous category.",
}


# ---------------------------------------------------------------------------
# 5.  SEED FUNCTION
# ---------------------------------------------------------------------------

def get_or_create_food_label(session: Session, name: FoodItemLabelName) -> FoodItemLabel:
    label = session.exec(
        select(FoodItemLabel).where(FoodItemLabel.name == name)
    ).first()
    if not label:
        label = FoodItemLabel(
            name=name,
            description=LABEL_DESCRIPTIONS.get(name, ""),
        )
        session.add(label)
        session.flush()
        print(f"  [NEW food label] {name}")
    return label


def get_or_create_food_item(session: Session, data: dict) -> FoodItem:
    item = session.exec(
        select(FoodItem).where(FoodItem.name == data["name"])
    ).first()
    if item:
        print(f"  [EXISTS food item] {data['name']}")
        return item

    item = FoodItem(
        name=data["name"],
        description=data.get("description"),
        nutrition_unit=data["nutrition_unit"],
        weight_per_unit_g=data.get("weight_per_unit_g"),
        calories=data["calories"],
        protein_g=data["protein_g"],
        carbs_g=data["carbs_g"],
        fat_g=data["fat_g"],
        is_verified=data.get("is_verified", True),
    )
    session.add(item)
    session.flush()  # get item.id

    # attach labels
    for label_name in data["labels"]:
        label = get_or_create_food_label(session, label_name)
        existing_link = session.exec(
            select(FoodItemLabelLink).where(
                FoodItemLabelLink.food_item_id == item.id,
                FoodItemLabelLink.food_item_label_id == label.id,
            )
        ).first()
        if not existing_link:
            session.add(FoodItemLabelLink(food_item_id=item.id, food_item_label_id=label.id))

    print(f"  [NEW food item] {data['name']}")
    return item


def get_or_create_meal_label(session: Session, name: MealLabelName) -> MealLabel:
    label = session.exec(
        select(MealLabel).where(MealLabel.name == name)
    ).first()
    if not label:
        label = MealLabel(
            name=name,
            description=MEAL_LABEL_DESCRIPTIONS.get(name, ""),
        )
        session.add(label)
        session.flush()
        print(f"  [NEW meal label] {name}")
    return label


def seed_meals(session: Session):
    print("\n=== Seeding Food Labels ===")
    for label_name in sorted(ALL_LABEL_NAMES_USED, key=lambda x: x.value):
        get_or_create_food_label(session, label_name)

    print("\n=== Seeding Food Items ===")
    food_item_map: dict[str, FoodItem] = {}
    for fi_data in FOOD_ITEMS_DATA:
        fi = get_or_create_food_item(session, fi_data)
        food_item_map[fi_data["name"]] = fi

    print("\n=== Seeding Meal Labels ===")
    for label_name in sorted(ALL_MEAL_LABEL_NAMES_USED, key=lambda x: x.value):
        get_or_create_meal_label(session, label_name)

    print("\n=== Seeding Meals ===")
    for meal_data in MEALS_DATA:
        existing = session.exec(
            select(Meal).where(Meal.name == meal_data["name"])
        ).first()
        if existing:
            print(f"  [EXISTS meal] {meal_data['name']}")
            continue

        meal = Meal(
            name=meal_data["name"],
            description=meal_data.get("description"),
            instructions=meal_data.get("instructions"),
            image_url=meal_data.get("image_url"),
            servings=meal_data["servings"],
            total_weight_g=meal_data.get("total_weight_g"),
            calories=meal_data["calories"],
            protein_g=meal_data["protein_g"],
            carbs_g=meal_data["carbs_g"],
            fat_g=meal_data["fat_g"],
            is_verified=meal_data.get("is_verified", True),
        )
        session.add(meal)
        session.flush()

        # food items
        for item_name, quantity, unit in meal_data["ingredients"]:
            fi = food_item_map.get(item_name)
            if fi is None:
                print(f"    [WARN] food item not found in seed map: {item_name}")
                continue
            session.add(
                MealFoodItem(
                    meal_id=meal.id,
                    food_item_id=fi.id,
                    quantity=quantity,
                    unit=unit,
                )
            )

        # labels
        for label_name in meal_data["labels"]:
            label = get_or_create_meal_label(session, label_name)
            existing_link = session.exec(
                select(MealLabelLink).where(
                    MealLabelLink.meal_id == meal.id,
                    MealLabelLink.meal_label_id == label.id,
                )
            ).first()
            if not existing_link:
                session.add(MealLabelLink(meal_id=meal.id, meal_label_id=label.id))

        print(f"  [NEW meal] {meal_data['name']}")

    session.commit()
    print("\n✅  Seeding complete!")


# ---------------------------------------------------------------------------
# 6.  ENTRY POINT
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    with Session(engine) as session:
        seed_meals(session)
