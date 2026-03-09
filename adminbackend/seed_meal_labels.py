"""Seed MealLabel table with all MealLabelName enum values."""
import os
import uuid
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))

LABELS = [
    "breakfast", "lunch", "dinner", "snack",
    "main_meal", "side_meal", "drink", "dessert",
    "halal", "vegetarian", "vegan",
    "high_protein", "low_carb", "gym_friendly",
    "other",
]

existing = supabase.table("meal_label").select("name").execute().data or []
existing_names = {r["name"] for r in existing}

now_str = datetime.now(timezone.utc).isoformat()
to_insert = []
for label in LABELS:
    if label not in existing_names:
        to_insert.append({
            "id": str(uuid.uuid4()),
            "name": label,
        })

if to_insert:
    supabase.table("meal_label").insert(to_insert).execute()
    print(f"Inserted {len(to_insert)} meal labels.")
else:
    print("All meal labels already exist.")
