import json
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from sqlmodel import Session
from supabase import create_client, Client
import os

from app.core.database import get_session
from app.core.auth import get_current_user
from app.modules.user.models import User
from app.modules.meal.models import Meal
from app.modules.meal.models import LikedMeal
from sqlmodel import select

router = APIRouter(prefix="/meals", tags=["Meals"])

def get_supabase() -> Client:
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))


def _resolve_ingredients(supabase: Client, rows: list) -> None:
    """Replace each meal row's JSON `ingredients` with the API shape
    [{food_item_name, quantity, unit}] via one batched food_item lookup."""
    ids = {
        ing.get("food_item_id")
        for m in rows
        for ing in (m.get("ingredients") or [])
        if ing.get("food_item_id")
    }
    names = {}
    if ids:
        fi_rows = (
            supabase.table("food_item").select("id, name").in_("id", list(ids)).execute().data or []
        )
        names = {fi["id"]: fi["name"] for fi in fi_rows}
    for m in rows:
        m["ingredients"] = [
            {
                "food_item_name": names.get(ing.get("food_item_id")),
                "quantity": ing.get("quantity"),
                "unit": ing.get("unit"),
            }
            for ing in (m.get("ingredients") or [])
        ]


# ── User: Browse meals ────────────────────────────────────────────────────────
@router.get("")
def list_meals(
    q: Optional[str] = Query(None, description="Search by meal name"),
    label: Optional[str] = Query(None, description="Filter by meal label"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    me: User = Depends(get_current_user),
):
    """Browse the master meal catalogue. Optionally filter by name or label."""
    supabase = get_supabase()
    query = (
        supabase.table("meal")
        .select("*")
        .order("name")
        .range(skip, skip + limit - 1)
    )
    if q:
        query = query.ilike("name", f"%{q}%")
    if label:
        # JSONB containment on the labels array — filters before pagination.
        # (JSON syntax required for jsonb columns; a Python list would produce
        # the native-array '{...}' literal and fail.)
        query = query.contains("labels", json.dumps([label]))

    results = query.execute().data or []
    _resolve_ingredients(supabase, results)
    return results


@router.get("/liked")
def get_liked_meals(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """Get all meals liked by the current user."""
    stmt = (
        select(Meal)
        .join(LikedMeal, LikedMeal.meal_id == Meal.id)
        .where(LikedMeal.user_id == me.id)
        .offset(skip)
        .limit(limit)
    )
    liked_meals = session.exec(stmt).all()
    
    # We will format this similar to the main list endpoint but keep it simpler
    # or just return the Meal objects directly for the frontend to consume.
    return liked_meals

@router.get("/{meal_id}")
def get_meal(
    meal_id: uuid.UUID,
    me: User = Depends(get_current_user),
):
    """Get full details of a specific meal."""
    supabase = get_supabase()
    query = (
        supabase.table("meal")
        .select("*")
        .eq("id", str(meal_id))
        .single()
    )
    result = query.execute().data
    if not result:
        raise HTTPException(status_code=404, detail="Meal not found")

    _resolve_ingredients(supabase, [result])
    return result

# ── Liked Meals ───────────────────────────────────────────────────────────────
@router.post("/{meal_id}/like")
def like_meal(
    meal_id: uuid.UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """Like a specific meal."""
    meal = session.get(Meal, meal_id)
    if not meal:
        raise HTTPException(status_code=404, detail="Meal not found")
        
    liked_meal = session.get(LikedMeal, (me.id, meal_id))
    if not liked_meal:
        liked_meal = LikedMeal(user_id=me.id, meal_id=meal_id)
        session.add(liked_meal)
        session.commit()
    return {"message": "Meal liked successfully"}


@router.delete("/{meal_id}/like")
def unlike_meal(
    meal_id: uuid.UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """Unlike a specific meal."""
    liked_meal = session.get(LikedMeal, (me.id, meal_id))
    if liked_meal:
        session.delete(liked_meal)
        session.commit()
    return {"message": "Meal unliked successfully"}


# ── Image upload ──────────────────────────────────────────────────────────────
@router.post("/{meal_id}/upload-image")
async def upload_meal_image(
    meal_id: uuid.UUID,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    meal = session.get(Meal, meal_id)
    if not meal:
        raise HTTPException(status_code=404, detail="Meal not found")
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    try:
        supabase = get_supabase()
        file_bytes = await file.read()
        file_ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
        unique_filename = f"{meal_id}-{uuid.uuid4().hex[:8]}.{file_ext}"
        supabase.storage.from_("meal-images").upload(path=unique_filename, file=file_bytes, file_options={"content-type": file.content_type})
        public_url = supabase.storage.from_("meal-images").get_public_url(unique_filename)
        meal.image_url = public_url
        session.add(meal); session.commit(); session.refresh(meal)
        return {"message": "Image uploaded successfully", "image_url": public_url}
    except Exception as e:
        print(f"Failed to upload image: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload image: {str(e)}")
