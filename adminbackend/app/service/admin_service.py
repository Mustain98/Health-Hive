import json
from datetime import datetime, timezone
from typing import Optional, List
import uuid

from fastapi import HTTPException

from core.supabase_client import supabase
from core.labels import FOOD_ITEM_LABELS, MEAL_LABELS


def _now():
    return datetime.now(timezone.utc).isoformat()


def _jsonb_contains(query, column: str, value):
    """PostgREST `cs` filter with JSON syntax (JSONB columns need '["x"]', not '{x}')."""
    return query.contains(column, json.dumps(value))


# ── Stats ─────────────────────────────────────────────────────────────────────

def _count(table: str, select_col: str = "id", **eq_filters) -> int:
    q = supabase.table(table).select(select_col, count="exact")
    for col, val in eq_filters.items():
        q = q.eq(col, val)
    return q.execute().count or 0


def _status_breakdown(table: str, status_col: str = "status") -> dict:
    """Aggregate row counts by status. Only the status column is fetched — no personal data."""
    rows = supabase.table(table).select(status_col).execute().data or []
    out: dict = {}
    for r in rows:
        key = r.get(status_col) or "unknown"
        out[key] = out.get(key, 0) + 1
    return out


def get_stats():
    # Users: only user_type is fetched; aggregate in Python.
    user_rows = supabase.table("users").select("user_type").execute().data or []
    users_by_type: dict = {}
    for r in user_rows:
        t = r.get("user_type") or "unknown"
        users_by_type[t] = users_by_type.get(t, 0) + 1

    total_consultants = _count("consultant_profiles", "user_id")
    verified_consultants = _count("consultant_profiles", "user_id", is_verified=True)
    pending_verif = _count("consultant_profiles", "user_id", is_verified=False)
    pending_applications = _count("consultant_applications", status="pending")
    unverified_documents = _count("consultant_documents", is_verified=False)

    # Consultants needing review = those with at least one unverified doc
    unverified_doc_owners = (
        supabase.table("consultant_documents")
        .select("consultant_profile_id")
        .eq("is_verified", False)
        .execute()
        .data
        or []
    )
    consultants_needing_review = len({d["consultant_profile_id"] for d in unverified_doc_owners})

    appointments_by_status = _status_breakdown("appointments")
    upcoming_appointments = (
        supabase.table("appointments")
        .select("id", count="exact")
        .gte("scheduled_start_at", _now())
        .execute()
        .count
        or 0
    )

    consultation_requests_by_status = _status_breakdown("consultation_requests")

    total_meals = _count("meal")
    meals_enriched = (
        supabase.table("meal").select("id", count="exact").not_.is_("enriched_at", "null").execute().count or 0
    )
    total_food_items = _count("food_item")

    return {
        "total_users": len(user_rows),
        "users_by_type": users_by_type,
        "total_consultants": total_consultants,
        "verified_consultants": verified_consultants,
        "pending_verifications": pending_verif,
        "pending_applications": pending_applications,
        "unverified_documents": unverified_documents,
        "consultants_needing_review": consultants_needing_review,
        "total_appointments": sum(appointments_by_status.values()),
        "appointments_by_status": appointments_by_status,
        "upcoming_appointments": upcoming_appointments,
        "consultation_requests_by_status": consultation_requests_by_status,
        "total_meals": total_meals,
        "meals_enriched": meals_enriched,
        "meals_not_enriched": total_meals - meals_enriched,
        "total_food_items": total_food_items,
    }


# ── Users ─────────────────────────────────────────────────────────────────────

def get_all_users(search: Optional[str] = None):
    query = supabase.table("users").select("id, full_name, email, user_type")
    if search:
        query = query.or_(f"full_name.ilike.%{search}%,email.ilike.%{search}%")
    result = query.execute()

    return [
        {
            "id": user["id"],
            "full_name": user.get("full_name") or "N/A",
            "email": user["email"],
            "role": user.get("user_type"),
        }
        for user in (result.data or [])
    ]


# ── Consultations (privacy-safe aggregates only) ─────────────────────────────

def get_consultations_summary():
    """Booking-funnel overview. Deliberately selects ONLY consultant ids + statuses —
    never the issue text, requester identity, or any message content."""
    requests = (
        supabase.table("consultation_requests").select("consultant_user_id, status").execute().data or []
    )
    chats = (
        supabase.table("consultation_chats").select("consultant_user_id, status").execute().data or []
    )
    profiles = (
        supabase.table("consultant_profiles").select("user_id, display_name, is_verified").execute().data or []
    )
    profile_by_id = {p["user_id"]: p for p in profiles}

    totals = {"pending": 0, "accepted": 0, "declined": 0}
    per_consultant: dict = {}
    for r in requests:
        status = r.get("status") or "unknown"
        if status in totals:
            totals[status] += 1
        cid = r.get("consultant_user_id")
        bucket = per_consultant.setdefault(
            cid, {"pending": 0, "accepted": 0, "declined": 0, "open_chats": 0, "total": 0}
        )
        if status in ("pending", "accepted", "declined"):
            bucket[status] += 1
        bucket["total"] += 1

    open_chats = 0
    for c in chats:
        if c.get("status") == "open":
            open_chats += 1
            cid = c.get("consultant_user_id")
            if cid in per_consultant:
                per_consultant[cid]["open_chats"] += 1

    rows = []
    for cid, counts in per_consultant.items():
        prof = profile_by_id.get(cid) or {}
        rows.append({
            "consultant_user_id": cid,
            "display_name": prof.get("display_name"),
            "is_verified": bool(prof.get("is_verified")),
            **counts,
        })
    rows.sort(key=lambda r: r["total"], reverse=True)

    return {
        "totals": {**totals, "total": len(requests)},
        "open_chats": open_chats,
        "per_consultant": rows,
    }


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
            # Derived from file_path — the table has no file_name/file_type columns.
            "file_name": (file_path.rsplit("/", 1)[-1] if file_path else "Document"),
            "file_type": "application/pdf",
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
    query = supabase.table("food_item").select("*").order("name")
    if search:
        query = query.ilike("name", f"%{search}%")
    if label:
        query = _jsonb_contains(query, "labels", [label])

    return query.execute().data or []


def get_food_labels():
    return FOOD_ITEM_LABELS


def create_food_item(payload: dict):
    labels = payload.pop("labels", []) or []
    invalid = [l for l in labels if l not in FOOD_ITEM_LABELS]
    if invalid:
        raise HTTPException(status_code=422, detail=f"Invalid food labels: {invalid}")

    now_str = _now()
    res = supabase.table("food_item").insert({
        **payload,
        "id": str(uuid.uuid4()),
        "labels": labels,
        "created_at": now_str,
        "updated_at": now_str,
        "is_verified": True
    }).execute()

    if not res.data:
        raise ValueError("Failed to create food item")
    return res.data[0]


def delete_food_item(item_id: str):
    # Guard: refuse deletion while any meal still references this ingredient
    # (ingredients are JSON now — no FK protects us anymore).
    ref = (
        supabase.table("meal")
        .select("id", count="exact")
        .contains("ingredients", json.dumps([{"food_item_id": item_id}]))
        .execute()
    )
    if (ref.count or 0) > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Food item is used by {ref.count} meal(s). Remove it from those meals first.",
        )

    supabase.table("food_item").delete().eq("id", item_id).execute()
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


def _build_ingredient_rows(ingredients: List[dict]):
    """Resolve food items once, compute total macros, and normalize the JSON rows."""
    total = {"calories": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0}
    rows: List[dict] = []
    if not ingredients:
        return total, rows

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
        rows.append({
            "food_item_id": ing["food_item_id"],
            "quantity": float(ing["quantity"]),
            "unit": ing["unit"],
        })
    return total, rows


def _validate_meal_labels(labels: List[str]):
    invalid = [l for l in labels if l not in MEAL_LABELS]
    if invalid:
        raise HTTPException(status_code=422, detail=f"Invalid meal labels: {invalid}")


def _attach_ingredient_names(rows: List[dict]):
    """Replace each meal row's JSON ingredients with
    [{food_item_id, food_item_name, quantity, unit}] via one batched lookup."""
    ids = {
        ing.get("food_item_id")
        for m in rows
        for ing in (m.get("ingredients") or [])
        if ing.get("food_item_id")
    }
    names = {}
    if ids:
        fi_rows = supabase.table("food_item").select("id, name").in_("id", list(ids)).execute().data or []
        names = {fi["id"]: fi["name"] for fi in fi_rows}
    for m in rows:
        m["ingredients"] = [
            {
                "food_item_id": ing.get("food_item_id"),
                "food_item_name": names.get(ing.get("food_item_id")),
                "quantity": ing.get("quantity"),
                "unit": ing.get("unit"),
            }
            for ing in (m.get("ingredients") or [])
        ]


def get_meals(search: Optional[str] = None, label: Optional[List[str]] = None):
    query = supabase.table("meal").select("*").order("name")
    if search:
        query = query.ilike("name", f"%{search}%")
    if label:
        # Multiple labels = AND (meal must carry all of them); JSONB containment.
        for req_label in label:
            query = _jsonb_contains(query, "labels", [req_label])

    results = query.execute().data or []
    _attach_ingredient_names(results)
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
      ]
    }
    """
    now_str = _now()
    labels = payload.pop("labels", []) or []
    _validate_meal_labels(labels)
    ingredients = payload.pop("ingredients", []) or []
    servings = float(payload.get("servings", 1) or 1)

    total, ingredient_rows = _build_ingredient_rows(ingredients)
    meal_macros = {k: round(v / servings, 2) for k, v in total.items()}

    res = supabase.table("meal").insert({
        **payload,
        **meal_macros,
        "id": str(uuid.uuid4()),
        "labels": labels,
        "ingredients": ingredient_rows,
        "is_verified": True,
        "created_at": now_str,
        "updated_at": now_str,
    }).execute()
    if not res.data:
        raise ValueError("Failed to create meal")
    return res.data[0]


def update_meal(meal_id: str, payload: dict):
    now_str = _now()
    labels = payload.pop("labels", None)
    ingredients = payload.pop("ingredients", None)
    servings = float(payload.get("servings", 1) or 1)

    if labels is not None:
        _validate_meal_labels(labels)
        payload["labels"] = labels

    if ingredients is not None:
        total, ingredient_rows = _build_ingredient_rows(ingredients)
        payload.update({k: round(v / servings, 2) for k, v in total.items()})
        payload["ingredients"] = ingredient_rows

    payload["updated_at"] = now_str
    if "id" in payload:
        del payload["id"]  # don't accidentally update PK

    res = supabase.table("meal").update(payload).eq("id", meal_id).execute()
    if not res.data:
        raise ValueError("Failed to update meal")
    return res.data[0]


def delete_meal(meal_id: str):
    # meal_embedding.meal_id has an FK to meal — clear it first.
    supabase.table("meal_embedding").delete().eq("meal_id", meal_id).execute()
    supabase.table("meal").delete().eq("id", meal_id).execute()
    return {"success": True}

def upload_meal_image(meal_id: str, file_bytes: bytes, content_type: str, filename: str):
    meal_res = supabase.table("meal").select("id").eq("id", meal_id).execute()
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
    return MEAL_LABELS
