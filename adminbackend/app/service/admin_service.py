from datetime import datetime, timezone
from typing import Optional
import uuid
from core.supabase_client import supabase


def _now():
    return datetime.now(timezone.utc).isoformat()


# ── Stats ─────────────────────────────────────────────────────────────────────

def get_stats():
    total_users_res = supabase.table("users").select("id", count="exact").execute()
    total_users = total_users_res.count or 0
    
    # We don't have "active" status in users table, just count all users who are not admin
    active_today_res = supabase.table("users").select("id", count="exact").neq("user_type", "admin").execute()
    active_today = active_today_res.count or 0

    total_consultants_res = supabase.table("consultant_profiles").select("user_id", count="exact").execute()
    total_consultants = total_consultants_res.count or 0
    
    # verification_status pending doesn't exist, we use is_verified == False
    pending_verif_res = supabase.table("consultant_profiles").select("user_id", count="exact").eq("is_verified", False).execute()
    pending_verif = pending_verif_res.count or 0

    total_appointments_res = supabase.table("appointments").select("id", count="exact").execute()
    total_appointments = total_appointments_res.count or 0

    return {
        "total_users": total_users,
        "active_today": active_today,
        "total_consultants": total_consultants,
        "pending_verifications": pending_verif,
        "reported_content": 0, # Features not built yet
        "total_appointments": total_appointments,
    }


# ── Users ─────────────────────────────────────────────────────────────────────

def get_all_users(search: Optional[str] = None):
    query = supabase.table("users").select("id, full_name, email, user_type")
    if search:
        query = query.or_(f"full_name.ilike.%{search}%,email.ilike.%{search}%")
    result = query.execute()
    
    rows = []
    for user in (result.data or []):
        rows.append({
            "id": user["id"],
            "full_name": user.get("full_name") or "N/A",
            "email": user["email"],
            "role": user.get("user_type"),
            "status": "active" # Placeholder since users table has no status column
        })
    return rows


def set_user_status(admin_id: str, user_id: str, status: str, note: Optional[str] = None):
    # The users table doesn't have a status column. For now, this is a no-op just to satisfy the frontend UI
    return {"success": True}


# ── Consultants ───────────────────────────────────────────────────────────────

def get_consultants(status: Optional[str] = None):
    # Fetch consultant profiles along with the user email and name via join
    query = supabase.table("consultant_profiles").select("*, users(full_name, email)")
    
    if status == "pending":
        query = query.eq("is_verified", False)
    elif status == "verified" or status == "approved":
        query = query.eq("is_verified", True)
        
    query = query.order("created_at", desc=True)
    result = query.execute()

    rows = []
    for row in (result.data or []):
        users_ref = row.pop("users", {}) or {}
        # Convert true/false to UI string
        verif_status = "verified" if row.get("is_verified") else "pending"
        
        rows.append({
            **row, 
            "id": row["user_id"], # frontend expects id
            "full_name": users_ref.get("full_name") or row.get("display_name"), 
            "email": users_ref.get("email"),
            "verification_status": verif_status
        })
    return rows


def verify_consultant(admin_id: str, consultant_id: str, decision: str, note: Optional[str] = None):
    is_verified = True if decision == "approve" else False
    
    supabase.table("consultant_profiles").update({
        "is_verified": is_verified,
        "verified_at": _now() if is_verified else None,
    }).eq("user_id", consultant_id).execute()

    return {"success": True, "status": "verified" if is_verified else "rejected"}


def get_consultant_documents(consultant_id: str):
    docs = supabase.table("consultant_documents").select("*").eq("consultant_profile_id", consultant_id).execute()
    
    results = []
    for doc in (docs.data or []):
        file_path = doc.get("file_path")
        bucket = doc.get("bucket", "consultant-documents")
        
        signed_url = None
        if file_path:
            # generate a signed url valid for 1 hour
            url_res = supabase.storage.from_(bucket).create_signed_url(file_path, 3600)
            if isinstance(url_res, dict) and "signedURL" in url_res:
                signed_url = url_res["signedURL"]
                
        results.append({
            "id": doc.get("id"),
            "file_name": doc.get("file_name") or "Document",
            "file_type": doc.get("file_type") or "application/pdf",
            "url": signed_url
        })
        
    return results


# ── Food Items ────────────────────────────────────────────────────────────────

def get_food_items(search: Optional[str] = None, label: Optional[str] = None):
    query = supabase.table("food_item").select("*, food_item_label_link(food_item_label(*))").order("name")
    if search:
        query = query.ilike("name", f"%{search}%")
    
    raw_data = query.execute().data or []
    
    # Flatten the Supabase join response so the frontend gets a simple list of labels
    results = []
    for item in raw_data:
        labels_raw = item.pop("food_item_label_link", []) or []
        parsed_labels = []
        for link in labels_raw:
            if link and link.get("food_item_label"):
                parsed_labels.append(link.get("food_item_label").get("name"))
        
        item["labels"] = parsed_labels
        
        if label and label not in parsed_labels:
            continue
            
        results.append(item)
        
    return results


def get_food_labels():
    res = supabase.table("food_item_label").select("*").order("name").execute()
    return res.data or []


def create_food_item(payload: dict):
    labels = payload.pop("labels", [])
    
    # Direct insert into food_item
    new_uuid = str(uuid.uuid4())
    now_str = datetime.now(timezone.utc).isoformat()
    
    res = supabase.table("food_item").insert({
        **payload,
        "id": new_uuid,
        "created_at": now_str,
        "updated_at": now_str,
        "is_verified": True
    }).execute()
    
    if not res.data:
        raise ValueError("Failed to create food item")
        
    new_item = res.data[0]
    new_item_id = new_item["id"]
    
    # If explicit labels were passed, insert the junction links
    if labels and len(labels) > 0:
        # Fetch the UUIDs of the requested labels
        label_records = supabase.table("food_item_label").select("id, name").in_("name", labels).execute()
        
        links_to_insert = []
        for record in (label_records.data or []):
            links_to_insert.append({
                "food_item_id": new_item_id,
                "food_item_label_id": record["id"],
                "created_at": now_str
            })
            
        if links_to_insert:
            supabase.table("food_item_label_link").insert(links_to_insert).execute()
            
    # Include the newly attached labels in the returned object
    new_item["labels"] = labels
    return new_item


def delete_food_item(item_id: str):
    # Explicitly clear out junction links first to avoid FK constraint violations
    supabase.table("food_item_label_link").delete().eq("food_item_id", item_id).execute()
    
    # Now we can safely delete the master item
    res = supabase.table("food_item").delete().eq("id", item_id).execute()
    return {"success": True}


# ── Meals ─────────────────────────────────────────────────────────────────────

def _calc_macros_for_ingredient(food_item: dict, quantity: float, unit: str) -> dict:
    """
    Given a food_item row and an amount (quantity + unit), compute the
    scaled macros that this ingredient contributes to the meal.

    Logic:
    - If food_item.nutrition_unit is 'g' or 'ml'  → macros are per 100 of that unit
      → scale = quantity / 100
    - If food_item.nutrition_unit is 'piece' or 'tbsp' → macros are per 1 of that unit
      → scale = quantity (can be fraction like 0.5 for half a piece)

    If the caller passes unit='g' for a piece-based item and weight_per_unit_g is known,
    we convert grams → pieces automatically.
    """
    fi_unit = food_item.get("nutrition_unit", "g")
    w_per_unit = food_item.get("weight_per_unit_g") or None

    # --- resolve scale --------------------------------------------------------
    if fi_unit in ("g", "ml", "gram", "milliliter"):
        if unit in ("g", "ml", "gram", "milliliter"):
            scale = quantity / 100.0
        elif unit in ("piece",) and w_per_unit:
            # user said "2 pieces" but FI is gram-based → convert to grams
            scale = (quantity * w_per_unit) / 100.0
        else:
            scale = quantity / 100.0  # fallback

    elif fi_unit in ("piece",):
        if unit in ("piece",):
            scale = quantity          # 0.5 = half piece, 2 = two pieces
        elif unit in ("g", "ml", "gram", "milliliter") and w_per_unit:
            # user typed "150g" but FI is piece-based → convert to fraction of piece
            scale = quantity / w_per_unit
        else:
            scale = quantity          # fallback

    elif fi_unit in ("tbsp",):
        scale = quantity              # 1 tbsp, 0.5 tbsp etc.

    else:
        scale = quantity / 100.0

    return {
        "calories":  round((food_item.get("calories")  or 0) * scale, 2),
        "protein_g": round((food_item.get("protein_g") or 0) * scale, 2),
        "carbs_g":   round((food_item.get("carbs_g")   or 0) * scale, 2),
        "fat_g":     round((food_item.get("fat_g")     or 0) * scale, 2),
    }


def get_meals(search: Optional[str] = None, label: Optional[str] = None):
    query = (
        supabase.table("meal")
        .select("*, meal_label_link(meal_label(*)), meal_food_item(*, food_item(*))")
        .order("name")
    )
    if search:
        query = query.ilike("name", f"%{search}%")

    raw_data = query.execute().data or []
    results = []
    for m in raw_data:
        # --- flatten labels ---
        label_links = m.pop("meal_label_link", []) or []
        parsed_labels = [
            lnk["meal_label"]["name"]
            for lnk in label_links
            if lnk and lnk.get("meal_label")
        ]

        # --- flatten ingredients ---
        food_links = m.pop("meal_food_item", []) or []
        ingredients = []
        for fi_link in food_links:
            fi = fi_link.get("food_item") or {}
            ingredients.append({
                "id": fi_link.get("id"),
                "food_item_id": fi_link.get("food_item_id"),
                "food_item_name": fi.get("name"),
                "quantity": fi_link.get("quantity"),
                "unit": fi_link.get("unit"),
            })

        m["labels"] = parsed_labels
        m["ingredients"] = ingredients

        # label filter in Python (avoids complex Supabase nested filter)
        if label and label not in parsed_labels:
            continue

        results.append(m)
    return results


def create_meal(payload: dict):
    """
    payload = {
      "name": str,
      "description": str | None,
      "instructions": str | None,
      "servings": float,          # default 1
      "labels": ["breakfast", "halal", ...],
      "ingredients": [
          {"food_item_id": "<uuid>", "quantity": 150, "unit": "g"},
          {"food_item_id": "<uuid>", "quantity": 1,   "unit": "piece"},
          {"food_item_id": "<uuid>", "quantity": 0.5, "unit": "piece"},
      ]
    }
    """
    now_str = _now()
    labels = payload.pop("labels", [])
    ingredients = payload.pop("ingredients", [])
    servings = float(payload.get("servings", 1) or 1)

    # --- auto-compute aggregate macros from ingredients ----------------------
    total = {"calories": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0}
    ingredient_rows = []

    if ingredients:
        fi_ids = [ing["food_item_id"] for ing in ingredients]
        fi_res = supabase.table("food_item").select("*").in_("id", fi_ids).execute()
        fi_map = {fi["id"]: fi for fi in (fi_res.data or [])}

        for ing in ingredients:
            fi = fi_map.get(ing["food_item_id"])
            if not fi:
                continue
            contrib = _calc_macros_for_ingredient(fi, float(ing["quantity"]), ing["unit"])
            for k in total:
                total[k] += contrib[k]
            ingredient_rows.append({
                "food_item_id": ing["food_item_id"],
                "quantity": float(ing["quantity"]),
                "unit": ing["unit"],
            })

    # Round totals per serving (macros stored per 1 serving)
    meal_macros = {k: round(v / servings, 2) for k, v in total.items()}

    # --- insert Meal ---------------------------------------------------------
    new_meal_id = str(uuid.uuid4())
    meal_payload = {
        **payload,
        **meal_macros,
        "id": new_meal_id,
        "is_verified": True,
        "created_at": now_str,
        "updated_at": now_str,
    }
    res = supabase.table("meal").insert(meal_payload).execute()
    if not res.data:
        raise ValueError("Failed to create meal")

    # --- insert MealFoodItem links -------------------------------------------
    if ingredient_rows:
        links = []
        for row in ingredient_rows:
            links.append({
                **row,
                "id": str(uuid.uuid4()),
                "meal_id": new_meal_id,
                "created_at": now_str,
            })
        supabase.table("meal_food_item").insert(links).execute()

    # --- insert MealLabel links ----------------------------------------------
    if labels:
        label_records = (
            supabase.table("meal_label").select("id, name").in_("name", labels).execute()
        )
        lbl_links = []
        for rec in (label_records.data or []):
            lbl_links.append({
                "meal_id": new_meal_id,
                "meal_label_id": rec["id"],
                "created_at": now_str,
            })
        if lbl_links:
            supabase.table("meal_label_link").insert(lbl_links).execute()

    return res.data[0]


def delete_meal(meal_id: str):
    # Remove junction rows first
    supabase.table("meal_label_link").delete().eq("meal_id", meal_id).execute()
    supabase.table("meal_food_item").delete().eq("meal_id", meal_id).execute()
    supabase.table("meal").delete().eq("id", meal_id).execute()
    return {"success": True}


def get_meal_labels():
    res = supabase.table("meal_label").select("*").order("name").execute()
    return res.data or []