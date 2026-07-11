"""One-time, cached LLM enrichment of meals: estimated nutrients + free-text health context.

Cache gate: `Meal.enriched_hash` = sha256(meal source text). A meal is (re)enriched only when its
source text changes, so edits refresh automatically and generation never re-calls the LLM for
already-enriched meals.
"""
from __future__ import annotations

import hashlib

from pydantic import BaseModel
from sqlmodel import Session, select

from app.modules.meal.models import Meal
from app.modules.meal_planner_agent import llm as llm_mod
from app.modules.meal_planner_agent.embeddings import food_name_map, meal_base_text
from app.utils.time import utc_now


class MealEnrichment(BaseModel):
    sodium_mg: float
    fiber_g: float
    sugar_g: float
    health_context: str


_ENRICH_SYSTEM = """You are a nutrition expert. For the given meal, ESTIMATE its per-serving
sodium (mg), fiber (g) and sugar (g) from the name, ingredients and macros. Then write ONE concise
health-context sentence describing who/what the meal suits — mention relevant properties (e.g.
low/high sodium, high fiber, low sugar, heart-healthy, diabetic-friendly, low-GI) and any conditions
it fits or should be avoided for. Be realistic; do not invent exotic claims."""


def _source_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _fallback(meal: Meal) -> MealEnrichment:
    cals = meal.calories or 1
    tags = []
    if meal.protein_g and (meal.protein_g * 4) / cals >= 0.30:
        tags.append("high-protein")
    if meal.carbs_g is not None and (meal.carbs_g * 4) / cals <= 0.25:
        tags.append("low-carb")
    if meal.fat_g is not None and (meal.fat_g * 9) / cals <= 0.20:
        tags.append("low-fat")
    ctx = ("A " + ", ".join(tags) + " meal.") if tags else "A balanced meal."
    return MealEnrichment(sodium_mg=0, fiber_g=0, sugar_g=0, health_context=ctx)


def _enrich_one(meal: Meal, base_text: str) -> MealEnrichment:
    try:
        return llm_mod._structured(MealEnrichment).invoke(
            [("system", _ENRICH_SYSTEM), ("human", base_text)]
        )
    except Exception as e:  # noqa: BLE001
        print(f"[MealPlan] enrichment LLM failed for {meal.name!r}, using fallback: {e}")
        return _fallback(meal)


def ensure_meal_enrichment(session: Session) -> int:
    """Enrich verified meals whose source text changed (or were never enriched). Returns count."""
    meals = session.exec(select(Meal).where(Meal.is_verified == True)).all()  # noqa: E712
    now = utc_now()
    food_names = food_name_map(session)
    enriched = 0
    for meal in meals:
        base = meal_base_text(meal, food_names)
        h = _source_hash(base)
        if meal.enriched_hash == h:
            continue
        enr = _enrich_one(meal, base)
        meal.sodium_mg = max(0.0, float(enr.sodium_mg))
        meal.fiber_g = max(0.0, float(enr.fiber_g))
        meal.sugar_g = max(0.0, float(enr.sugar_g))
        meal.ai_health_context = enr.health_context
        meal.enriched_hash = h
        meal.enriched_at = now
        session.add(meal)
        enriched += 1
    if enriched:
        session.commit()
    return enriched
