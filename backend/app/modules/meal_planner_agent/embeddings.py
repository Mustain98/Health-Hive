"""Meal embeddings (local, all-MiniLM-L6-v2 via fastembed) + pgvector retrieval."""
from __future__ import annotations

import hashlib
import uuid
from functools import lru_cache
from typing import List

from sqlmodel import Session, select

from app.modules.meal.models import Meal, MealEmbedding, EMBEDDING_DIM

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def _embedder():
    # Lazy singleton — loads (and first-time downloads) the ONNX model once per process.
    from langchain_community.embeddings import FastEmbedEmbeddings
    return FastEmbedEmbeddings(model_name=EMBED_MODEL)


def embed_query(text: str) -> List[float]:
    return _embedder().embed_query(text)


def embed_documents(texts: List[str]) -> List[List[float]]:
    return _embedder().embed_documents(texts)


def meal_base_text(meal: Meal) -> str:
    """The meal's source text (name, description, instructions, labels, ingredients, macros).
    Used as the enrichment input + enrichment cache key. Excludes AI-derived fields."""
    parts: List[str] = [meal.name]
    if meal.description:
        parts.append(meal.description)
    if meal.instructions:
        parts.append(meal.instructions)

    labels = [lbl.name.value if hasattr(lbl.name, "value") else str(lbl.name) for lbl in meal.labels]
    if labels:
        parts.append("labels: " + ", ".join(labels))

    ingredients = [mfi.food_item.name for mfi in meal.meal_food_items if mfi.food_item]
    if ingredients:
        parts.append("ingredients: " + ", ".join(ingredients))

    parts.append(
        f"macros: {round(meal.calories)} kcal, "
        f"{round(meal.protein_g)}g protein, {round(meal.carbs_g)}g carbs, {round(meal.fat_g)}g fat"
    )
    return " | ".join(parts)


def meal_to_text(meal: Meal) -> str:
    """The text we embed: source text + the LLM health context + extra nutrients (semantic layer)."""
    parts = [meal_base_text(meal)]
    if meal.ai_health_context:
        parts.append("health: " + meal.ai_health_context)
    parts.append(
        f"extra: sodium ~{round(meal.sodium_mg or 0)}mg, "
        f"fiber ~{round(meal.fiber_g or 0)}g, sugar ~{round(meal.sugar_g or 0)}g"
    )
    return " | ".join(parts)


def _text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def ensure_meal_embeddings(session: Session) -> int:
    """Embed & upsert MealEmbedding rows for verified meals that are missing or stale.
    Returns the number of (re)embedded meals."""
    meals = session.exec(select(Meal).where(Meal.is_verified == True)).all()  # noqa: E712
    existing = {e.meal_id: e for e in session.exec(select(MealEmbedding)).all()}

    to_embed: list[tuple[Meal, str, str]] = []
    for meal in meals:
        text = meal_to_text(meal)
        h = _text_hash(text)
        cur = existing.get(meal.id)
        if cur is None or cur.text_hash != h:
            to_embed.append((meal, text, h))

    if not to_embed:
        return 0

    vectors = embed_documents([t for (_m, t, _h) in to_embed])
    for (meal, _text, h), vec in zip(to_embed, vectors):
        row = existing.get(meal.id)
        if row is None:
            row = MealEmbedding(meal_id=meal.id, text_hash=h, model=EMBED_MODEL, embedding=vec)
        else:
            row.text_hash = h
            row.model = EMBED_MODEL
            row.embedding = vec
        session.add(row)
    session.commit()
    return len(to_embed)


def retrieve_meal_ids(session: Session, query: str, k: int = 20) -> List[uuid.UUID]:
    """Return the meal_ids of the top-k verified meals nearest to the query (pgvector cosine)."""
    qvec = embed_query(query)
    rows = session.exec(
        select(MealEmbedding.meal_id)
        .join(Meal, Meal.id == MealEmbedding.meal_id)
        .where(Meal.is_verified == True)  # noqa: E712
        .order_by(MealEmbedding.embedding.cosine_distance(qvec))
        .limit(k)
    ).all()
    return list(rows)
