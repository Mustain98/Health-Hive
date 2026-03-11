from datetime import datetime, timezone
from typing import Optional, List
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
    
    # Unverified consultant profiles
    pending_verif_res = supabase.table("consultant_profiles").select("user_id", count="exact").eq("is_verified", False).execute()
    pending_verif = pending_verif_res.count or 0

    total_appointments_res = supabase.table("appointments").select("id", count="exact").execute()
    total_appointments = total_appointments_res.count or 0

    # Pending consultant applications
    pending_apps_res = supabase.table("consultant_applications").select("id", count="exact").eq("status", "pending").execute()
    pending_applications = pending_apps_res.count or 0

    # Unverified consultant documents
    unverified_docs_res = supabase.table("consultant_documents").select("id", count="exact").eq("is_verified", False).execute()
    unverified_documents = unverified_docs_res.count or 0

    # Consultants needing review = those who have at least one unverified doc
    unverified_doc_owners = supabase.table("consultant_documents").select("consultant_profile_id").eq("is_verified", False).execute().data or []
    consultants_needing_review = len(set(d["consultant_profile_id"] for d in unverified_doc_owners))

    return {
        "total_users": total_users,
        "active_today": active_today,
        "total_consultants": total_consultants,
        "pending_verifications": pending_verif,
        "reported_content": 0,
        "total_appointments": total_appointments,
        "pending_applications": pending_applications,
        "unverified_documents": unverified_documents,
        "consultants_needing_review": consultants_needing_review,
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
    # Fetch all consultant profiles with user info
    query = supabase.table("consultant_profiles").select("*, users!consultant_profiles_user_id_fkey(full_name, email)")
    query = query.order("created_at", desc=True)
    result = query.execute()

    # Fetch ALL consultant documents to determine which consultants have unverified docs
    all_docs = supabase.table("consultant_documents").select("consultant_profile_id, is_verified").execute().data or []
    
    # Build a set of consultant_profile_ids that have at least one unverified doc
    has_unverified = set()
    for d in all_docs:
        if not d.get("is_verified"):
            has_unverified.add(d["consultant_profile_id"])

    rows = []
    for row in (result.data or []):
        users_ref = row.pop("users", {}) or {}
        uid = row["user_id"]
        is_pending = uid in has_unverified
        verif_status = "pending" if is_pending else "verified"

        # Apply filter
        if status == "pending" and not is_pending:
            continue
        if status == "verified" and is_pending:
            continue

        rows.append({
            **row, 
            "id": uid,
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
            try:
                url_res = supabase.storage.from_(bucket).create_signed_url(file_path, 3600)
                if isinstance(url_res, dict) and "signedURL" in url_res:
                    signed_url = url_res["signedURL"]
            except Exception:
                pass
                
        results.append({
            "id": doc.get("id"),
            "doc_type": doc.get("doc_type"),
            "issuer": doc.get("issuer"),
            "issue_date": doc.get("issue_date"),
            "is_verified": doc.get("is_verified", False),
            "verification_note": doc.get("verification_note"),
            "file_name": doc.get("file_name") or "Document",
            "file_type": doc.get("file_type") or "application/pdf",
            "url": signed_url
        })
        
    return results


def review_consultant_document(consultant_id: str, doc_id: str, decision: str, note: Optional[str] = None):
    """Verify or reject (delete) a specific consultant document."""
    # Check doc exists and belongs to this consultant
    doc = supabase.table("consultant_documents").select("*").eq("id", doc_id).eq("consultant_profile_id", consultant_id).execute().data
    if not doc:
        return {"success": False, "error": "Document not found"}
    doc = doc[0]
    
    if decision == "approve":
        supabase.table("consultant_documents").update({
            "is_verified": True,
            "verification_note": note,
        }).eq("id", doc_id).execute()
        return {"success": True, "status": "verified"}
    else:
        # Reject = delete from table and storage
        file_path = doc.get("file_path")
        bucket = doc.get("bucket", "consultant-documents")
        if file_path:
            try:
                supabase.storage.from_(bucket).remove([file_path])
            except Exception:
                pass  # best-effort cleanup
        supabase.table("consultant_documents").delete().eq("id", doc_id).execute()
        return {"success": True, "status": "deleted"}


# ── Applications ──────────────────────────────────────────────────────────────

def get_applications(status: Optional[str] = None):
    query = supabase.table("consultant_applications").select("*, users(email, full_name)").order("created_at", desc=True)
    if status:
        query = query.eq("status", status)
        
    res = query.execute().data or []
    
    # Also fetch documents for each app
    if res:
        app_ids = [r["id"] for r in res]
        docs = supabase.table("application_documents").select("*").in_("application_id", app_ids).execute().data or []
        
        # Generate signed URLs for each document
        for d in docs:
            file_path = d.get("file_path")
            bucket = d.get("bucket", "application-documents")
            if file_path:
                try:
                    url_res = supabase.storage.from_(bucket).create_signed_url(file_path, 3600)
                    if isinstance(url_res, dict) and "signedURL" in url_res:
                        d["url"] = url_res["signedURL"]
                except Exception:
                    pass
        
        docs_by_app = {}
        for d in docs:
            docs_by_app.setdefault(d["application_id"], []).append(d)
            
        for r in res:
            # Flatten user join data
            users_ref = r.pop("users", {}) or {}
            r["email"] = users_ref.get("email")
            r["full_name"] = users_ref.get("full_name")
            r["documents"] = docs_by_app.get(r["id"], [])
            
    return res

def review_application(app_id: str, admin_id: str, decision: str, note: Optional[str] = None):
    # Fetch application
    app = supabase.table("consultant_applications").select("*").eq("id", app_id).single().execute().data
    if not app:
        return {"success": False, "error": "Application not found"}
        
    if decision == "approved":
        # Normalize consultant_type to lowercase (handles legacy uppercase data)
        consultant_type = (app.get("consultant_type") or "").lower()
        
        # Check if they already have a profile to avoid unique constraint violations
        existing = supabase.table("consultant_profiles").select("user_id").eq("user_id", app["user_id"]).execute().data
        if not existing:
            # 1. Create Profile
            now_ts = _now()
            supabase.table("consultant_profiles").insert({
                "user_id": app["user_id"],
                "display_name": app["display_name"],
                "bio": app["bio"],
                "specialties": app["specialties"],
                "other_info": app["other_info"],
                "consultant_type": consultant_type,
                "highest_qualification": app["highest_qualification"],
                "graduation_institution": app["graduation_institution"],
                "registration_body": app["registration_body"],
                "registration_number": app["registration_number"],
                "is_verified": True,
                "verified_at": now_ts,
                "created_at": now_ts,
                "updated_at": now_ts,
            }).execute()
        else:
             # Just verify them if they somehow have a profile
             supabase.table("consultant_profiles").update({
                "is_verified": True,
                "verified_at": _now()
            }).eq("user_id", app["user_id"]).execute()
            
        # 2. Update user type
        supabase.table("users").update({"user_type": "consultant"}).eq("id", app["user_id"]).execute()
        
        # 3. Move Documents — physically copy to consultant-documents matching regular upload logic
        docs = supabase.table("application_documents").select("*").eq("application_id", app_id).execute().data or []
        doc_now = _now()
        import hashlib
        for d in docs:
            doc_type = (d.get("doc_type") or "").lower()
            old_bucket = d["bucket"]
            old_path = d["file_path"]
            
            try:
                # 1. Download original file bytes
                raw = supabase.storage.from_(old_bucket).download(old_path)
                
                # 2. Hash it like add_document_supabase does
                sha = hashlib.sha256(raw).hexdigest()
                
                # 3. Upload to consultant-documents at exact expected path
                new_bucket = "consultant-documents"
                new_path = f"docs/{app['user_id']}/{sha}.pdf"
                
                supabase.storage.from_(new_bucket).upload(
                    path=new_path,
                    file=raw,
                    file_options={"content-type": "application/pdf", "upsert": "true"}
                )
                
                # 4. Insert DB record pointing to the newly generated file
                supabase.table("consultant_documents").insert({
                    "id": str(uuid.uuid4()),
                    "consultant_profile_id": app["user_id"],
                    "doc_type": doc_type,
                    "issuer": d.get("issuer"),
                    "issue_date": d.get("issue_date"),
                    "expires_at": d.get("expires_at"),
                    "bucket": new_bucket,
                    "file_path": new_path,
                    "file_hash": sha,
                    "is_verified": True,   # Automatically verify docs on approval
                    "created_at": doc_now,
                }).execute()
                
            except Exception as e:
                print(f"Warning: Failed to copy and insert document {old_path}: {e}")
                # We do not fallback here because the user explicitly wants docs in the primary bucket.
                # If it fails, the document won't copy over.

    # 4. Update Application Status
    supabase.table("consultant_applications").update({
        "status": decision,
        "admin_note": note,
        "updated_at": _now()
    }).eq("id", app_id).execute()
    
    return {"success": True, "status": decision}


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


def get_meals(search: Optional[str] = None, label: Optional[List[str]] = None):
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
        if label:
            # We treat multiple labels as an AND condition (must have all requested labels)
            if not all(req_label in parsed_labels for req_label in label):
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


def update_meal(meal_id: str, payload: dict):
    now_str = _now()
    labels = payload.pop("labels", None)
    ingredients = payload.pop("ingredients", None)
    servings = float(payload.get("servings", 1) or 1)

    # --- auto-compute aggregate macros if ingredients were provided ---
    if ingredients is not None:
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

        # Round totals per serving
        meal_macros = {k: round(v / servings, 2) for k, v in total.items()}
        payload.update(meal_macros)

    # --- update Meal ---------------------------------------------------------
    payload["updated_at"] = now_str
    if "id" in payload:
        del payload["id"] # don't accidentally update PK
        
    res = supabase.table("meal").update(payload).eq("id", meal_id).execute()
    if not res.data:
        raise ValueError("Failed to update meal")

    # --- update MealFoodItem links (clear & recreate) ------------------------
    if ingredients is not None:
        supabase.table("meal_food_item").delete().eq("meal_id", meal_id).execute()
        if ingredient_rows:
            links = []
            for row in ingredient_rows:
                links.append({
                    **row,
                    "id": str(uuid.uuid4()),
                    "meal_id": meal_id,
                    "created_at": now_str,
                })
            supabase.table("meal_food_item").insert(links).execute()

    # --- update MealLabel links (clear & recreate) ---------------------------
    if labels is not None:
        supabase.table("meal_label_link").delete().eq("meal_id", meal_id).execute()
        if labels:
            label_records = supabase.table("meal_label").select("id, name").in_("name", labels).execute()
            lbl_links = []
            for rec in (label_records.data or []):
                lbl_links.append({
                    "meal_id": meal_id,
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

def upload_meal_image(meal_id: str, file_bytes: bytes, content_type: str, filename: str):
    import uuid
    meal_res = supabase.table("meal").select("*").eq("id", meal_id).execute()
    if not meal_res.data:
        raise ValueError("Meal not found")
        
    file_ext = filename.split(".")[-1] if "." in filename else "jpg"
    unique_filename = f"{meal_id}-{uuid.uuid4().hex[:8]}.{file_ext}"
    
    # Upload to storage
    try:
        supabase.storage.from_("meal-images").upload(
            path=unique_filename,
            file=file_bytes,
            file_options={"content-type": content_type}
        )
    except Exception as e:
        raise ValueError(f"Failed to upload image to bucket: {str(e)}")
        
    public_url = supabase.storage.from_("meal-images").get_public_url(unique_filename)
    
    # Update meal record
    supabase.table("meal").update({"image_url": public_url, "updated_at": _now()}).eq("id", meal_id).execute()
    
    return {"message": "Image uploaded successfully", "image_url": public_url}


def get_meal_labels():
    res = supabase.table("meal_label").select("*").order("name").execute()
    return res.data or []