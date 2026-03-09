import os
import uuid
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase: Client = create_client(url, key)

labels = [
    "grain", "meat", "fish", "dairy", "vegetable", "fruit", 
    "legume", "nut_seed", "oil_fat", "beverage", "spice", "sweetener",
    "halal", "vegetarian", "vegan",
    "egg", "gluten", "nuts", "shellfish", "soy",
    "high_protein", "high_fiber", "low_carb", "low_fat"
]

print(f"Populating {len(labels)} labels...")
now_str = datetime.utcnow().isoformat()

success = 0
for label in labels:
    try:
        # Check if exists first
        existing = supabase.table("food_item_label").select("id").eq("name", label).execute()
        if not existing.data:
            supabase.table("food_item_label").insert({
                "id": str(uuid.uuid4()),
                "name": label,
                "created_at": now_str
            }).execute()
            success += 1
            print(f"Added {label}")
        else:
            print(f"Skipped {label} (already exists)")
    except Exception as e:
        print(f"Failed to add {label}: {e}")

print(f"Done! Successfully added {success} new labels.")
