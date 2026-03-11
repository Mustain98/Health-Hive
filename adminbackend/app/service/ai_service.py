"""
ai_service.py — Groq-powered food item generation.

When an Admin searches for a food item that doesn't exist in the database,
the frontend calls POST /api/admin/food-items/generate, which routes here.
We prompt Groq (Llama) to return a structured JSON matching FoodItemSchema,
validate the response, and insert the new FoodItem into the database.
"""
import os
import json
import re
import uuid
from datetime import datetime, timezone

from groq import Groq
from core.supabase_client import supabase


GROQ_API_KEY = os.getenv("GROQ_API_KEY")

VALID_LABELS = {
    "grain",
    "meat",
    "fish",
    "dairy",
    "vegetable",
    "fruit",
    "legume",
    "nut_seed",
    "oil_fat",
    "beverage",
    "spice",
    "sweetener",
    "halal",
    "vegetarian",
    "vegan",
    "egg",
    "gluten",
    "nuts",
    "shellfish",
    "soy",
    "high_protein",
    "high_fiber",
    "low_carb",
    "low_fat",
    "other",
}

SYSTEM_PROMPT = """You are a professional nutritionist database assistant.
Given a food item name/description, respond with ONLY a valid JSON object
with the following fields (no markdown, no explanation, pure JSON):

{
  "name": "string — properly formatted food name",
  "nutrition_unit": "gram" | "milliliter" | "piece" | "tbsp",
  "weight_per_unit_g": <number or null — grams per one piece/tbsp, null if gram/ml based>,
  "calories": <number>,
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
- Use ONLY labels from the provided list
- Do NOT invent new labels
- If no label fits, use "other"

Very important consistency rules:
- If nutrition_unit is "gram", values must be for 100g
- If nutrition_unit is "milliliter", values must be for 100ml
- If nutrition_unit is "piece", values must be for exactly 1 piece
- If nutrition_unit is "tbsp", values must be for exactly 1 tablespoon
- Do NOT use per-100g values when nutrition_unit is milliliter
- Do NOT use per-100g values when nutrition_unit is tbsp
- For oils, prefer nutrition_unit="tbsp" rather than "milliliter"
- For fruits like banana/apple and foods like egg, prefer nutrition_unit="piece"
- For standard solids like rice, oats, chicken, yogurt, use nutrition_unit="gram"
- For drinks like milk/juice, use nutrition_unit="milliliter"

Examples:
- Olive Oil -> nutrition_unit="tbsp", calories about 119, fat_g about 13.5
- Milk -> nutrition_unit="milliliter", calories about 61, protein_g about 3.2, carbs_g about 4.8, fat_g about 3.3
- Boiled Egg -> nutrition_unit="piece", calories about 78, protein_g about 6.3, fat_g about 5.3
- Banana -> nutrition_unit="piece", calories about 105, carbs_g about 27
- Cooked White Rice -> nutrition_unit="gram", calories about 130, carbs_g about 28
- Be realistic with macros based on USDA or well-known nutrition databases
"""


def normalize_labels(labels) -> list[str]:
    if not isinstance(labels, list):
        return []

    normalized = []
    seen = set()

    for label in labels:
        if not isinstance(label, str):
            continue

        value = label.strip().lower()
        if value in VALID_LABELS and value not in seen:
            normalized.append(value)
            seen.add(value)

    return normalized


def normalize_generated_food_item(parsed: dict) -> dict:
    name = str(parsed.get("name", "")).strip().lower()
    unit = parsed.get("nutrition_unit", "gram")

    calories = float(parsed.get("calories", 0) or 0)
    fat_g = float(parsed.get("fat_g", 0) or 0)

    # Oils should usually be tablespoon-based in this system
    if "oil" in name and unit == "milliliter":
        parsed["nutrition_unit"] = "tbsp"
        parsed["weight_per_unit_g"] = 13.5

        # If model likely returned per-100g oil values, correct them
        if calories > 300 or fat_g > 30:
            parsed["calories"] = 119
            parsed["protein_g"] = 0
            parsed["carbs_g"] = 0
            parsed["fat_g"] = 13.5

    # Milk should not have unrealistic per-100ml values
    if "milk" in name and parsed.get("nutrition_unit") == "milliliter":
        if calories > 150 or fat_g > 15:
            parsed["calories"] = 61
            parsed["protein_g"] = 3.2
            parsed["carbs_g"] = 4.8
            parsed["fat_g"] = 3.3

    # Piece/tbsp should not carry huge per-100g style values
    if parsed.get("nutrition_unit") == "tbsp" and calories > 250:
        if "oil" in name:
            parsed["calories"] = 119
            parsed["protein_g"] = 0
            parsed["carbs_g"] = 0
            parsed["fat_g"] = 13.5

    if parsed.get("nutrition_unit") in {"gram", "milliliter"}:
        parsed["weight_per_unit_g"] = None

    return parsed


def validate_food_item_payload(parsed: dict) -> None:
    unit = parsed.get("nutrition_unit")

    calories = float(parsed.get("calories", 0) or 0)
    protein_g = float(parsed.get("protein_g", 0) or 0)
    carbs_g = float(parsed.get("carbs_g", 0) or 0)
    fat_g = float(parsed.get("fat_g", 0) or 0)

    if unit in {"gram", "milliliter"}:
        if calories > 900 or protein_g > 100 or carbs_g > 100 or fat_g > 100:
            raise ValueError("Generated nutrition values look invalid for gram/milliliter basis.")

    if unit == "piece":
        if calories > 500:
            raise ValueError("Generated nutrition values look invalid for piece basis.")

    if unit == "tbsp":
        if calories > 250:
            raise ValueError("Generated nutrition values look invalid for tbsp basis.")


def generate_food_item(query: str) -> dict:
    """
    Ask Groq/Llama to derive a FoodItem for `query`, insert it into the DB,
    and return the new row (with labels).
    """
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not configured in the environment.")

    client = Groq(api_key=GROQ_API_KEY)

    chat_completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Food item: {query}"},
        ],
        model="llama-3.3-70b-versatile",
        temperature=0.2,
    )
    raw_text = chat_completion.choices[0].message.content.strip()

    # Strip backtick code blocks if Groq wrapped the response
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned).strip()

    parsed = json.loads(cleaned)

    # Normalize nutrition_unit to what the Postgres ENUM expects
    unit_map = {
        "gram": "gram",
        "grams": "gram",
        "g": "gram",
        "milliliter": "milliliter",
        "ml": "milliliter",
        "piece": "piece",
        "pieces": "piece",
        "tbsp": "tbsp",
        "tablespoon": "tbsp",
    }
    parsed["nutrition_unit"] = unit_map.get(
        str(parsed.get("nutrition_unit", "gram")).lower(),
        "gram",
    )

    parsed = normalize_generated_food_item(parsed)
    validate_food_item_payload(parsed)

    labels = normalize_labels(parsed.pop("labels", []))
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
    if labels:
        lbl_records = (
            supabase.table("food_item_label")
            .select("id, name")
            .in_("name", labels)
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

    new_item["labels"] = labels
    return new_item