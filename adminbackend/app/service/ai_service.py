"""
ai_service.py — Gemini-powered food item generation.

When an Admin searches for a food item that doesn't exist in the database,
the frontend calls POST /api/admin/food-items/generate, which routes here.
We prompt Gemini Flash to return a structured JSON matching FoodItemSchema,
validate the response, and insert the new FoodItem into the database.
"""
import os
import json
import re
import uuid
from datetime import datetime, timezone

from google import genai
from core.supabase_client import supabase


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

SYSTEM_PROMPT = """You are a professional nutritionist database assistant.
Given a food item name/description, respond with ONLY a valid JSON object
with the following fields (no markdown, no explanation, pure JSON):

{
  "name": "string — properly formatted food name",
  "nutrition_unit": "gram" | "milliliter" | "piece" | "tbsp",
  "weight_per_unit_g": <number or null — grams per one piece/tbsp, null if gram/ml based>,
  "calories": <number — kcal per 100g OR per piece/tbsp based on nutrition_unit>,
  "protein_g": <number>,
  "carbs_g": <number>,
  "fat_g": <number>,
  "labels": ["array of applicable labels from: grain, meat, fish, dairy, vegetable, fruit, legume, nut_seed, oil_fat, beverage, spice, sweetener, halal, vegetarian, vegan, egg, gluten, nuts, shellfish, soy, high_protein, high_fiber, low_carb, low_fat, other"]
}

Rules:
- nutrition_unit=gram means macros are per 100 grams
- nutrition_unit=milliliter means macros are per 100 ml
- nutrition_unit=piece means macros are per 1 whole piece (provide weight_per_unit_g if known)
- nutrition_unit=tbsp means macros are per 1 tablespoon
- Be realistic with macros based on USDA or well-known nutrition databases
- Include appropriate dietary labels
"""


def generate_food_item(query: str) -> dict:
    """
    Ask Gemini to derive a FoodItem for `query`, insert it into the DB,
    and return the new row (with labels).
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not configured in the environment.")

    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = f"{SYSTEM_PROMPT}\n\nFood item: {query}"

    response = client.models.generate_content(
        model="gemini-1.5-flash",
        contents=prompt,
    )
    raw_text = response.text.strip()

    # Strip backtick code blocks if Gemini wrapped the response
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned).strip()

    parsed = json.loads(cleaned)

    # Normalize nutrition_unit to what the Postgres ENUM expects
    unit_map = {
        "gram": "gram", "grams": "gram", "g": "gram",
        "milliliter": "milliliter", "ml": "milliliter",
        "piece": "piece", "pieces": "piece",
        "tbsp": "tbsp", "tablespoon": "tbsp",
    }
    parsed["nutrition_unit"] = unit_map.get(
        str(parsed.get("nutrition_unit", "gram")).lower(), "gram"
    )

    labels = parsed.pop("labels", [])
    now_str = datetime.now(timezone.utc).isoformat()
    new_id = str(uuid.uuid4())

    # Insert into food_item table
    res = supabase.table("food_item").insert({
        "id": new_id,
        "name": parsed["name"],
        "nutrition_unit": parsed["nutrition_unit"],
        "weight_per_unit_g": parsed.get("weight_per_unit_g"),
        "calories": float(parsed.get("calories", 0)),
        "protein_g": float(parsed.get("protein_g", 0)),
        "carbs_g": float(parsed.get("carbs_g", 0)),
        "fat_g": float(parsed.get("fat_g", 0)),
        "is_verified": True,
        "created_at": now_str,
        "updated_at": now_str,
    }).execute()

    if not res.data:
        raise ValueError("DB insert failed after AI generation.")

    new_item = res.data[0]

    # Link labels
    valid_labels = [l for l in labels if isinstance(l, str) and l.strip()]
    if valid_labels:
        lbl_records = (
            supabase.table("food_item_label")
            .select("id, name")
            .in_("name", valid_labels)
            .execute()
        )
        links = [
            {
                "food_item_id": new_id,
                "food_item_label_id": rec["id"],
                "created_at": now_str,
            }
            for rec in (lbl_records.data or [])
        ]
        if links:
            supabase.table("food_item_label_link").insert(links).execute()

    new_item["labels"] = valid_labels
    return new_item
