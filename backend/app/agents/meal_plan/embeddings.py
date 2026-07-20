"""Meal embeddings (Jina embeddings API) + pgvector retrieval."""
from __future__ import annotations

import logging
import uuid
from typing import Dict, List, Optional

from sqlmodel import Session, select

from app.modules.meal.models import FoodItem, Meal, MealEmbedding, EMBEDDING_DIM
from app.core import embeddings as _emb
from app.core.embeddings import EmbeddingUnavailable  # noqa: F401  (re-exported for callers)
from app.core.llm.settings import EMBED_MODEL

logger = logging.getLogger(__name__)


def embed_documents(texts: List[str]) -> List[List[float]]:
    return _emb.embed_documents(texts, EMBEDDING_DIM)


def embed_query(text: str) -> List[float]:
    return _emb.embed_query(text, EMBEDDING_DIM)


def food_name_map(session: Session) -> Dict[str, str]:
    """{food_item_id (str): name} for resolving ingredient names from the JSON column."""
    rows = session.exec(select(FoodItem.id, FoodItem.name)).all()
    return {str(fid): name for fid, name in rows}


def meal_base_text(meal: Meal, food_names: Optional[Dict[str, str]] = None) -> str:
    """The meal's source text (name, description, instructions, labels, ingredients, macros).
    Used as the enrichment input + enrichment cache key. Excludes AI-derived fields."""
    parts: List[str] = [meal.name]
    if meal.description:
        parts.append(meal.description)
    if meal.instructions:
        parts.append(meal.instructions)

    labels = list(meal.labels or [])
    if labels:
        parts.append("labels: " + ", ".join(labels))

    food_names = food_names or {}
    ingredients = [
        food_names[ing.get("food_item_id")]
        for ing in (meal.ingredients or [])
        if ing.get("food_item_id") in food_names
    ]
    if ingredients:
        parts.append("ingredients: " + ", ".join(ingredients))

    parts.append(
        f"macros: {round(meal.calories)} kcal, "
        f"{round(meal.protein_g)}g protein, {round(meal.carbs_g)}g carbs, {round(meal.fat_g)}g fat"
    )
    return " | ".join(parts)


def meal_to_text(meal: Meal, food_names: Optional[Dict[str, str]] = None) -> str:
    """The text we embed: source text + the LLM health context + extra nutrients (semantic layer)."""
    parts = [meal_base_text(meal, food_names)]
    if meal.ai_health_context:
        parts.append("health: " + meal.ai_health_context)
    parts.append(
        f"extra: sodium ~{round(meal.sodium_mg or 0)}mg, "
        f"fiber ~{round(meal.fiber_g or 0)}g, sugar ~{round(meal.sugar_g or 0)}g"
    )
    return " | ".join(parts)


_text_hash = _emb.text_hash


def ensure_meal_embeddings(session: Session) -> int:
    """Embed & upsert MealEmbedding rows for verified meals that are missing or stale.
    Returns the number of (re)embedded meals. Skips (returns 0) if the Jina API is
    unavailable — existing embeddings stay usable; vectors from different models are
    never mixed (the model column is part of the staleness check)."""
    meals = session.exec(select(Meal).where(Meal.is_verified == True)).all()  # noqa: E712
    existing = {e.meal_id: e for e in session.exec(select(MealEmbedding)).all()}
    food_names = food_name_map(session)

    to_embed: list[tuple[Meal, str, str]] = []
    for meal in meals:
        text = meal_to_text(meal, food_names)
        h = _text_hash(text)
        cur = existing.get(meal.id)
        if cur is None or cur.text_hash != h or cur.model != EMBED_MODEL:
            to_embed.append((meal, text, h))

    if not to_embed:
        return 0

    try:
        vectors = embed_documents([t for (_m, t, _h) in to_embed])
    except EmbeddingUnavailable as exc:
        logger.warning("Skipping meal re-embedding: %s", exc)
        return 0

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


def retrieve_meal_ids(session: Session, query: str, k: int = 20) -> Optional[List[uuid.UUID]]:
    """Return the meal_ids of the top-k verified meals nearest to the query (pgvector cosine).
    Returns None (distinct from []) when the embedding API is unavailable so callers
    can fall back to non-semantic retrieval."""
    try:
        qvec = embed_query(query)
    except EmbeddingUnavailable as exc:
        logger.warning("Semantic retrieval unavailable, caller should fall back: %s", exc)
        return None
    rows = session.exec(
        select(MealEmbedding.meal_id)
        .join(Meal, Meal.id == MealEmbedding.meal_id)
        .where(Meal.is_verified == True)  # noqa: E712
        .where(MealEmbedding.model == EMBED_MODEL)
        .order_by(MealEmbedding.embedding.cosine_distance(qvec))
        .limit(k)
    ).all()
    return list(rows)
