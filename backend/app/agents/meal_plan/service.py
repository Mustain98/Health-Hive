"""meal_plan_service.py — LLM-constrained, vector-retrieval meal plan generation.

Pipeline (per generation, computed once and reused across days):
  1. resolve the daily macro target (active NutritionTarget, or auto-suggested via TDEE + LLM)
  2. LLM emits a per-timed-meal constraint (macros + composition + labels + retrieval query)
  3. retrieve a meal pool per slot via pgvector similarity (+ hard allergen/diet filters)
  4. a deterministic assembler builds & selects combos within each constraint
  5. persist MealCombo + TimedMealComboOption (variety across days by rotating the chosen option)
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException
from sqlmodel import Session, select

from app.modules.meal.models import FoodItem, Meal, MealCombo, MealComboItem, TimedMeal, TimedMealComboOption, DayMealPlan, LikedMeal, WeekMealPlan
from app.core.enums import MealLabelName, MealTimeType
from app.modules.meal_plan_setting.models import MealPlanSetting, MealPlanSettingTimedMeal
from app.modules.nutrition_target.models import NutritionTarget
from app.modules.user.models import UserData, UserAllergen, UserPreference, UserHealthProfile
from app.modules.milestone.models import Milestone
from app.utils.time import utc_now
from app.utils.calculate import calculate_tdee
from app.agents.meal_plan import embeddings as emb
from app.agents.meal_plan.agent import generate_constraints
from app.modules.nutrition_target.services.suggest import suggest_nutrition_target
from app.modules.meal_plan_setting.services.suggest import suggest_meal_structure
from app.agents.enrichment import agent as enr
from app.modules.notification.services import notification as notif_service
from app.modules.notification.models import NotificationType

_DEFAULT_SLOTS = [
    {"meal_time": "breakfast", "name": "Breakfast", "calories_pct": 25},
    {"meal_time": "lunch", "name": "Lunch", "calories_pct": 35},
    {"meal_time": "dinner", "name": "Dinner", "calories_pct": 30},
    {"meal_time": "snack", "name": "Snack", "calories_pct": 10},
]

CANDIDATE_COUNT = 20
COMBO_PICK_COUNT = 5
POOL_K = 25
SERVING_CAP = 3.0
SERVING_MIN = 0.5

_VALID_MEAL_TIMES = {mt.value for mt in MealTimeType}

# Diet preference -> disallowed FoodItem label names (hard filter over ingredients).
_DIET_DISALLOWED = {
    "vegan": {"meat", "fish", "dairy", "egg", "shellfish"},
    "vegetarian": {"meat", "fish", "shellfish"},
    "pescatarian": {"meat"},
}


# ═══════════════════════════════════════════════════════════════════════════
# Serving math + persistence (reused from the previous rule-based generator)
# ═══════════════════════════════════════════════════════════════════════════

def _calc_combo_macros(meals_with_servings: List[Tuple[Meal, float]]) -> Dict[str, float]:
    total = {"calories": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0}
    for meal, servings in meals_with_servings:
        total["calories"] += meal.calories * servings
        total["protein_g"] += meal.protein_g * servings
        total["carbs_g"] += meal.carbs_g * servings
        total["fat_g"] += meal.fat_g * servings
    return {k: round(v, 1) for k, v in total.items()}


def _adjust_servings(combo_meals: List[Meal], target: Dict[str, float]) -> List[Tuple[Meal, float]]:
    """Scale the WHOLE combo by one factor so its total calories approach the slot target.
    (Scaling every item together — rather than only the main + fixed sides — keeps totals on
    target for both small/weight-loss and large/muscle-gain slots.)"""
    if not combo_meals:
        return []
    base_cals = sum(m.calories for m in combo_meals)
    tcal = target.get("calories", 0) or 0
    scale = (tcal / base_cals) if (base_cals > 0 and tcal > 0) else 1.0
    scale = max(SERVING_MIN, min(SERVING_CAP, round(scale, 1)))
    return [(m, scale) for m in combo_meals]


def _persist_combo(session: Session, meals_with_servings, macros, meal_time: MealTimeType, name: str) -> MealCombo:
    combo = MealCombo(
        name=name, meal_time=meal_time,
        calories=macros["calories"], protein_g=macros["protein_g"],
        carbs_g=macros["carbs_g"], fat_g=macros["fat_g"],
    )
    session.add(combo)
    session.flush()
    for meal, servings in meals_with_servings:
        session.add(MealComboItem(meal_combo_id=combo.id, meal_id=meal.id, quantity=servings))
    return combo


def _coerce_meal_time(value: str) -> MealTimeType:
    """Normalize any (possibly LLM-invented) meal_time to a valid MealTimeType.
    The DB column is a native enum, so out-of-enum strings would crash the INSERT."""
    v = (value or "").strip().lower()
    if v in _VALID_MEAL_TIMES:
        return MealTimeType(v)
    # Keyword map — check 'snack' FIRST so "mid-morning snack" -> snack (not breakfast).
    if "snack" in v:
        return MealTimeType.snack
    if "breakfast" in v or "morning" in v:
        return MealTimeType.breakfast
    if "lunch" in v or "noon" in v:
        return MealTimeType.lunch
    if "dinner" in v or "supper" in v or "evening" in v:
        return MealTimeType.dinner
    return MealTimeType.snack  # any other extra eating occasion (brunch, pre-workout, …)


# ═══════════════════════════════════════════════════════════════════════════
# Profile + macro target
# ═══════════════════════════════════════════════════════════════════════════

def _active_target(session: Session, user_id: uuid.UUID) -> Optional[NutritionTarget]:
    return session.exec(
        select(NutritionTarget)
        .where(NutritionTarget.created_for == user_id, NutritionTarget.active == True)  # noqa: E712
    ).first()


def _active_goal(session: Session, user_id: uuid.UUID) -> Optional[Milestone]:
    return session.exec(
        select(Milestone).where(Milestone.created_for == user_id, Milestone.active == True)  # noqa: E712
    ).first()


def _active_setting(session: Session, user_id: uuid.UUID) -> Optional[MealPlanSetting]:
    return session.exec(
        select(MealPlanSetting)
        .where(MealPlanSetting.created_for == user_id, MealPlanSetting.active == True)  # noqa: E712
    ).first()


def assemble_profile(session: Session, user_id: uuid.UUID) -> dict:
    ud = session.exec(select(UserData).where(UserData.user_id == user_id)).first()
    goal = _active_goal(session, user_id)
    health = session.get(UserHealthProfile, user_id)

    allergen_ids = set(session.exec(
        select(UserAllergen.food_item_id).where(UserAllergen.user_id == user_id)
    ).all())
    allergen_names = []
    if allergen_ids:
        allergen_names = [
            f.name for f in session.exec(select(FoodItem).where(FoodItem.id.in_(list(allergen_ids)))).all()
        ]

    liked_meal_names = [
        m.name for m in session.exec(
            select(Meal).join(LikedMeal, LikedMeal.meal_id == Meal.id).where(LikedMeal.user_id == user_id)
        ).all()
    ]

    return {
        "body": None if not ud else {
            "age": ud.age, "gender": ud.gender.value if ud.gender else None,
            "height_cm": ud.height_cm, "weight_kg": ud.weight_kg,
            "activity_level": ud.activity_level.value if ud.activity_level else None,
        },
        "goal": None if not goal else {
            "goal_type": goal.goal_type.value if hasattr(goal.goal_type, "value") else goal.goal_type,
            "target_weight": goal.target_weight, "duration_days": goal.duration_days,
        },
        "diet_preferences": (health.diet_preferences if health else []) or [],
        "health_conditions": (health.health_conditions if health else []) or [],
        "health_notes": health.notes if health else None,
        "allergies": allergen_names,
        "liked_meals": liked_meal_names[:15],
    }


def resolve_macro_target(session: Session, user_id: uuid.UUID, profile: dict) -> Dict[str, float]:
    """Use the user's ACTIVE NutritionTarget. Activation is always explicit now —
    generation never silently overwrites the target (the old 'auto' path is gone;
    use POST /meal-plans/resolve-setup to generate + activate)."""
    target = _active_target(session, user_id)
    if not target:
        raise HTTPException(400, "No active nutrition target")
    return {
        "calories": float(target.calories_kcal),
        "protein_g": float(target.protein_g),
        "carbs_g": float(target.carbs_g),
        "fat_g": float(target.fat_g),
    }


def require_active_setup(session: Session, user_id: uuid.UUID) -> None:
    """Gate: a meal plan needs BOTH an active nutrition target and an active meal
    setting. Otherwise 409 with a structured body so the UI can offer consult-or-AI."""
    missing = []
    if not _active_target(session, user_id):
        missing.append("nutrition_target")
    if not _active_setting(session, user_id):
        missing.append("meal_plan_setting")
    if missing:
        raise HTTPException(status_code=409, detail={
            "needs_setup": True,
            "missing": missing,
            "options": ["consultation", "ai_generate"],
            "message": "Set up your nutrition target and meal setting before generating a plan.",
        })


def _persist_nutrition_target(session: Session, user_id: uuid.UUID, s) -> NutritionTarget:
    now = utc_now()
    for t in session.exec(select(NutritionTarget).where(
        NutritionTarget.created_for == user_id, NutritionTarget.active == True)  # noqa: E712
    ).all():
        t.active = False
        session.add(t)
    target = NutritionTarget(
        created_for=user_id, created_by=user_id, active=True,
        calories_kcal=int(s.calories_kcal), protein_g=float(s.protein_g),
        carbs_g=float(s.carbs_g), fat_g=float(s.fat_g), created_at=now, updated_at=now,
    )
    session.add(target)
    session.commit()
    session.refresh(target)
    return target


def _setting_slots(setting: Optional[MealPlanSetting]) -> Optional[List[dict]]:
    if not setting:
        return None
    slots = []
    for tm in setting.timed_meals:
        mt = tm.meal_time.value if hasattr(tm.meal_time, "value") else tm.meal_time
        labels = [l.value if hasattr(l, "value") else l for l in (tm.meal_labels or [])]
        slots.append({
            "meal_time": mt, "name": tm.name, "labels": labels,
            "calories_pct": tm.calories_pct or None,
        })
    return slots or None


# ═══════════════════════════════════════════════════════════════════════════
# Retrieval pool (pgvector) + hard filters
# ═══════════════════════════════════════════════════════════════════════════

def _diet_disallowed_food_labels(diet_prefs: List[str]) -> set:
    out: set = set()
    for d in diet_prefs:
        out |= _DIET_DISALLOWED.get(d, set())
    return out


def _meal_ingredient_ids(meal: Meal) -> set:
    """Ingredient food_item ids as uuid.UUID (the JSON column stores strings)."""
    out: set = set()
    for ing in meal.ingredients or []:
        fid = ing.get("food_item_id")
        if not fid:
            continue
        try:
            out.add(uuid.UUID(str(fid)))
        except ValueError:
            continue
    return out


def _fallback_pool_ids(session: Session, constraint, k: int = POOL_K) -> List[uuid.UUID]:
    """Non-semantic pool when the embedding API is unavailable: verified meals filtered
    by the constraint's labels (required labels, else the slot's meal_time, else any),
    ordered by calorie proximity to the slot target. Deterministic — generation never dies."""
    from sqlalchemy import func

    target_cal = float(getattr(constraint.macros, "calories", 0) or 0)

    def _query(labels: List[str]) -> List[uuid.UUID]:
        stmt = select(Meal.id).where(Meal.is_verified == True)  # noqa: E712
        for lbl in labels:
            stmt = stmt.where(Meal.labels.contains([lbl]))
        stmt = stmt.order_by(func.abs(Meal.calories - target_cal)).limit(k)
        return list(session.exec(stmt).all())

    for labels in (list(constraint.required_labels or []), [constraint.meal_time], []):
        ids = _query([l for l in labels if l])
        if ids:
            return ids
    return []


def build_pool(session: Session, user_id: uuid.UUID, constraint, ctx: dict) -> List[Dict[str, Any]]:
    """Retrieve top meals for the constraint's query, apply hard allergen/diet filters, add like boosts."""
    meal_ids = emb.retrieve_meal_ids(session, constraint.retrieval_query, k=POOL_K)
    if meal_ids is None:  # embedding API unavailable — non-semantic fallback
        meal_ids = _fallback_pool_ids(session, constraint, k=POOL_K)
    if not meal_ids:
        return []
    meals = session.exec(select(Meal).where(Meal.id.in_(meal_ids))).all()
    order = {mid: i for i, mid in enumerate(meal_ids)}
    meals.sort(key=lambda m: order.get(m.id, 999))

    allergen_ids: set = ctx["allergen_food_ids"]
    disallowed_labels: set = ctx["disallowed_food_labels"]
    liked_food_ids: set = ctx["liked_food_ids"]
    liked_meal_ids: set = ctx["liked_meal_ids"]

    # Prefetch food-item labels for every ingredient in the pool (one query) —
    # needed for diet-preference exclusion now that labels live on the JSON column.
    fi_labels: Dict[uuid.UUID, set] = {}
    if disallowed_labels:
        all_ing_ids = set()
        for meal in meals:
            all_ing_ids |= _meal_ingredient_ids(meal)
        if all_ing_ids:
            for fid, lbls in session.exec(
                select(FoodItem.id, FoodItem.labels).where(FoodItem.id.in_(all_ing_ids))
            ).all():
                fi_labels[fid] = set(lbls or [])

    pool: List[Dict[str, Any]] = []
    for meal in meals:
        ingredient_fi_ids = _meal_ingredient_ids(meal)
        # hard: allergen exclusion
        if ingredient_fi_ids & allergen_ids:
            continue
        # hard: diet-preference exclusion via ingredient food-item labels
        if disallowed_labels:
            ing_labels: set = set()
            for fid in ingredient_fi_ids:
                ing_labels |= fi_labels.get(fid, set())
            if ing_labels & disallowed_labels:
                continue

        meal_label_names = list(meal.labels or [])
        label_set = set(meal_label_names)
        score = 0.0
        # likes
        if meal.id in liked_meal_ids:
            score += 3
        score += len(ingredient_fi_ids & liked_food_ids)
        # validated enum label overlap
        score += 2 * len(set(constraint.required_labels) & label_set)
        score += 1 * len(set(constraint.preferred_labels) & label_set)
        # slot meal_time affinity
        if constraint.meal_time in label_set:
            score += 0.5
        # nutrient fit (soft): reward meeting condition-driven limits, gently penalize clear misses
        if constraint.max_sodium_mg is not None:
            score += 1.0 if (meal.sodium_mg or 0) <= constraint.max_sodium_mg else -0.5
        if constraint.min_fiber_g is not None:
            score += 1.0 if (meal.fiber_g or 0) >= constraint.min_fiber_g else -0.25
        if constraint.max_sugar_g is not None:
            score += 1.0 if (meal.sugar_g or 0) <= constraint.max_sugar_g else -0.5
        pool.append({
            "meal": meal, "labels": meal_label_names,
            "ingredient_fi_ids": ingredient_fi_ids, "score": score,
        })
    return pool


def _retrieval_ctx(session: Session, user_id: uuid.UUID, profile: dict) -> dict:
    allergen_ids = set(session.exec(
        select(UserAllergen.food_item_id).where(UserAllergen.user_id == user_id)
    ).all())
    liked_food_ids = set(session.exec(
        select(UserPreference.food_item_id).where(UserPreference.user_id == user_id)
    ).all())
    liked_meal_ids = set(session.exec(
        select(LikedMeal.meal_id).where(LikedMeal.user_id == user_id)
    ).all())
    return {
        "allergen_food_ids": allergen_ids,
        "liked_food_ids": liked_food_ids,
        "liked_meal_ids": liked_meal_ids,
        "disallowed_food_labels": _diet_disallowed_food_labels(profile.get("diet_preferences", [])),
    }


# ═══════════════════════════════════════════════════════════════════════════
# Deterministic combo assembly + selection
# ═══════════════════════════════════════════════════════════════════════════

def _macro_distance(macros: Dict[str, float], target: Dict[str, float]) -> float:
    dist = 0.0
    for key in ("calories", "protein_g", "carbs_g", "fat_g"):
        t = target.get(key, 0)
        if t > 0:
            dist += abs(macros[key] - t) / t
    return dist


def assemble_and_select(pool: List[Dict[str, Any]], constraint) -> List[Dict[str, Any]]:
    """Build candidate combos honoring the constraint, then pick the best COMBO_PICK_COUNT deterministically."""
    if not pool:
        return []
    target = constraint.macros.model_dump()
    comp = constraint.composition
    allow_multi = (comp.max_items or 1) > 1 or "side" in [c.lower() for c in (comp.components or [])]

    candidates: List[Dict[str, Any]] = []
    seen_keys: set = set()

    tcal = target.get("calories", 0) or 0
    for main_entry in pool[:CANDIDATE_COUNT]:
        main_meal = main_entry["meal"]
        combo_meals = [main_meal]
        combo_score = main_entry["score"]

        # Add a side only if allowed AND the main alone leaves calorie room (< 90% of target) —
        # otherwise a second item just overshoots the slot's calories.
        if allow_multi and len(pool) > 1 and main_meal.calories < tcal * 0.9:
            # deterministic complementary pick: highest protein-per-calorie among the rest
            best_side = None
            best_ppc = -1.0
            for e in pool:
                m = e["meal"]
                if m.id == main_meal.id:
                    continue
                ppc = (m.protein_g / m.calories) if m.calories > 0 else 0
                if ppc > best_ppc:
                    best_ppc, best_side = ppc, e
            if best_side:
                combo_meals.append(best_side["meal"])
                combo_score += best_side["score"] * 0.3

        meals_with_servings = _adjust_servings(combo_meals, target)
        macros = _calc_combo_macros(meals_with_servings)
        key = tuple(sorted(m.id for m, _ in meals_with_servings))
        if key in seen_keys:
            continue
        seen_keys.add(key)
        dist = _macro_distance(macros, target)
        candidates.append({
            "key": key, "meals": meals_with_servings, "macros": macros,
            "rank_score": -dist + 0.05 * combo_score,
        })

    candidates.sort(key=lambda c: c["rank_score"], reverse=True)
    return candidates[:COMBO_PICK_COUNT]


# ═══════════════════════════════════════════════════════════════════════════
# Generation
# ═══════════════════════════════════════════════════════════════════════════

def _compute_context(session: Session, user_id: uuid.UUID) -> dict:
    """Everything computed once per generation and reused across days."""
    require_active_setup(session, user_id)  # gate before any expensive work
    enr.ensure_meal_enrichment(session)   # estimate nutrients + health context (cached)
    emb.ensure_meal_embeddings(session)   # embed enriched text (cached)
    profile = assemble_profile(session, user_id)
    macro_target = resolve_macro_target(session, user_id, profile)
    setting = _active_setting(session, user_id)
    slots = _setting_slots(setting)
    plan = generate_constraints(
        profile, macro_target, slots, allowed_labels=[m.value for m in MealLabelName]
    )

    ctx = _retrieval_ctx(session, user_id, profile)
    pools = [build_pool(session, user_id, c, ctx) for c in plan.slots]
    return {"macro_target": macro_target, "constraints": plan.slots, "pools": pools}


def _generate_timed_meal(session: Session, timed_meal: TimedMeal, constraint, pool, day_of_week: int) -> dict:
    chosen_selections = assemble_and_select(pool, constraint)
    if not chosen_selections:
        return {"timed_meal_id": str(timed_meal.id), "meal_time": constraint.meal_time,
                "error": "No meals matched the constraints", "combo_options": []}

    # clear old options
    for opt in session.exec(
        select(TimedMealComboOption).where(TimedMealComboOption.timed_meal_id == timed_meal.id)
    ).all():
        session.delete(opt)
    session.flush()

    meal_time = _coerce_meal_time(constraint.meal_time)
    chosen_rank = (day_of_week % len(chosen_selections)) + 1  # rotate chosen per weekday for variety
    combo_options_out = []
    chosen_combo_id = None
    chosen_macros = None

    for rank_idx, cand in enumerate(chosen_selections):
        combo_name = " + ".join(m.name for m, _ in cand["meals"])
        combo = _persist_combo(session, cand["meals"], cand["macros"], meal_time, combo_name)
        is_chosen = (rank_idx + 1) == chosen_rank
        session.add(TimedMealComboOption(
            timed_meal_id=timed_meal.id, meal_combo_id=combo.id, is_chosen=is_chosen, rank=rank_idx + 1,
        ))
        if is_chosen:
            chosen_combo_id = combo.id
            chosen_macros = cand["macros"]
        combo_options_out.append({
            "rank": rank_idx + 1, "is_chosen": is_chosen, "combo_id": str(combo.id),
            "combo_name": combo_name, "macros": cand["macros"],
            "meals": [{"name": m.name, "servings": s, "meal_id": str(m.id)} for m, s in cand["meals"]],
        })

    if chosen_combo_id and chosen_macros:
        timed_meal.meal_combo_id = chosen_combo_id
        timed_meal.calories = chosen_macros["calories"]
        timed_meal.protein_g = chosen_macros["protein_g"]
        timed_meal.carbs_g = chosen_macros["carbs_g"]
        timed_meal.fat_g = chosen_macros["fat_g"]
        session.add(timed_meal)

    session.flush()
    return {
        "timed_meal_id": str(timed_meal.id), "meal_time": constraint.meal_time,
        "target_macros": constraint.macros.model_dump(), "combo_options": combo_options_out,
    }


def _find_user_day(session: Session, user_id: uuid.UUID, day_of_week: int) -> Optional[DayMealPlan]:
    """The user's existing DayMealPlan for a weekday, or None.
    Enforces the 'one day per weekday per user' invariant used by overlap resolution."""
    return session.exec(
        select(DayMealPlan)
        .join(WeekMealPlan, WeekMealPlan.id == DayMealPlan.week_plan_id)
        .where(WeekMealPlan.user_id == user_id, DayMealPlan.day_of_week == day_of_week)
    ).first()


def _get_or_create_week_plan(session: Session, user_id: uuid.UUID) -> WeekMealPlan:
    """The user's single recurring Mon-Sun plan, created on first use."""
    wp = session.exec(select(WeekMealPlan).where(WeekMealPlan.user_id == user_id)).first()
    if wp is None:
        wp = WeekMealPlan(title="Weekly Meal Plan", user_id=user_id, status="active")
        session.add(wp)
        session.flush()
    return wp


def _slot_conflicts(day_plan: DayMealPlan) -> List[dict]:
    """Existing slots on a day, as overlap-conflict descriptors."""
    return [
        {
            "timed_meal_id": str(tm.id),
            "day_of_week": day_plan.day_of_week,
            "meal_time": tm.meal_time.value if hasattr(tm.meal_time, "value") else str(tm.meal_time),
        }
        for tm in day_plan.timed_meals
    ]


def _constraint_index_for(ctx: dict, meal_time_val: str) -> int:
    return next(
        (i for i, c in enumerate(ctx["constraints"]) if _coerce_meal_time(c.meal_time).value == meal_time_val),
        0,
    )


def _build_fresh_day(session: Session, ctx: dict, day_of_week: int, week_plan_id: uuid.UUID) -> dict:
    """Create a brand-new day (all slots) under the user's week plan."""
    day_plan = DayMealPlan(week_plan_id=week_plan_id, day_of_week=day_of_week)
    session.add(day_plan)
    session.flush()
    results = []
    for slot_idx, constraint in enumerate(ctx["constraints"]):
        timed_meal = TimedMeal(day_plan_id=day_plan.id, meal_time=_coerce_meal_time(constraint.meal_time))
        session.add(timed_meal)
        session.flush()
        results.append(_generate_timed_meal(session, timed_meal, constraint, ctx["pools"][slot_idx], day_of_week))
    return {"day_plan_id": str(day_plan.id), "day_of_week": day_of_week, "timed_meals": results}


def _overwrite_existing_day(session: Session, ctx: dict, day_plan: DayMealPlan,
                            overwrite_ids: set) -> dict:
    """In an already-existing day, regenerate only the slots whose id is in overwrite_ids;
    keep the rest untouched. Does not add new slots (delete + regenerate for that)."""
    results = []
    for tm in day_plan.timed_meals:
        if tm.id in overwrite_ids:
            idx = _constraint_index_for(
                ctx, tm.meal_time.value if hasattr(tm.meal_time, "value") else str(tm.meal_time))
            results.append(_generate_timed_meal(
                session, tm, ctx["constraints"][idx], ctx["pools"][idx], day_plan.day_of_week))
    return {"day_plan_id": str(day_plan.id), "day_of_week": day_plan.day_of_week,
            "timed_meals": results, "kept_existing": True}


def generate_day_plan(session: Session, user_id: uuid.UUID, day_of_week: int,
                      overwrite_ids: Optional[set] = None) -> dict:
    existing = _find_user_day(session, user_id, day_of_week)

    if existing and existing.timed_meals and overwrite_ids is None:
        raise HTTPException(status_code=409, detail={
            "overlap": True, "day_of_week": day_of_week, "conflicts": _slot_conflicts(existing),
        })

    ctx = _compute_context(session, user_id)
    if existing:
        result = _overwrite_existing_day(session, ctx, existing, overwrite_ids or set())
    else:
        wp = _get_or_create_week_plan(session, user_id)
        result = _build_fresh_day(session, ctx, day_of_week, wp.id)
    session.commit()
    return result


def generate_week_plan(session: Session, user_id: uuid.UUID, days: Optional[List[int]] = None,
                       overwrite_ids: Optional[set] = None) -> dict:
    """Generate the requested weekdays (default: the whole Mon-Sun week).

    Day intersection: the requested days that are *already* planned are the conflicts. Without
    an overwrite allowlist that's a 409; with one, only the allowlisted slots on those days are
    regenerated and every other requested day is created fresh."""
    days = sorted(set(days if days is not None else range(7)))
    existing_by_day = {d: _find_user_day(session, user_id, d) for d in days}

    conflicts = []
    conflicting_days = []
    for d in days:
        ex = existing_by_day[d]
        if ex and ex.timed_meals:
            conflicting_days.append(d)
            conflicts.extend(_slot_conflicts(ex))

    if conflicts and overwrite_ids is None:
        raise HTTPException(status_code=409, detail={
            "overlap": True, "days": conflicting_days, "conflicts": conflicts,
        })

    ctx = _compute_context(session, user_id)  # constraints + pools computed once
    overwrite_ids = overwrite_ids or set()
    wp = _get_or_create_week_plan(session, user_id)

    day_results = []
    for d in days:
        ex = existing_by_day[d]
        if ex:
            day_results.append(_overwrite_existing_day(session, ctx, ex, overwrite_ids))
        else:
            day_results.append(_build_fresh_day(session, ctx, d, wp.id))

    session.commit()
    return {"week_plan_id": str(wp.id), "days": day_results}


def regenerate_timed_meal(session: Session, user_id: uuid.UUID, timed_meal_id: uuid.UUID) -> dict:
    timed_meal = _authorize_timed_meal(session, user_id, timed_meal_id)
    ctx = _compute_context(session, user_id)
    meal_time_val = timed_meal.meal_time.value if hasattr(timed_meal.meal_time, "value") else str(timed_meal.meal_time)
    idx = _constraint_index_for(ctx, meal_time_val)
    dow = timed_meal.day_plan.day_of_week
    result = _generate_timed_meal(session, timed_meal, ctx["constraints"][idx], ctx["pools"][idx], dow)
    session.commit()
    return result


def regenerate_day_plan(session: Session, user_id: uuid.UUID, day_plan_id: uuid.UUID) -> dict:
    """Regenerate every slot on an existing day in place."""
    day_plan = _authorize_day_plan(session, user_id, day_plan_id)
    ctx = _compute_context(session, user_id)
    results = []
    for tm in day_plan.timed_meals:
        idx = _constraint_index_for(
            ctx, tm.meal_time.value if hasattr(tm.meal_time, "value") else str(tm.meal_time))
        results.append(_generate_timed_meal(
            session, tm, ctx["constraints"][idx], ctx["pools"][idx], day_plan.day_of_week))
    session.commit()
    return {"day_plan_id": str(day_plan.id), "day_of_week": day_plan.day_of_week, "timed_meals": results}


# ═══════════════════════════════════════════════════════════════════════════
# Setup suggestion (LLM tool-callable)
# ═══════════════════════════════════════════════════════════════════════════

def suggest_setup(session: Session, user_id: uuid.UUID, apply: bool = False) -> dict:
    """Suggest a nutrition target + meal structure via the LLM. Persists the target if apply=True."""
    profile = assemble_profile(session, user_id)
    body = profile.get("body")
    tdee = None
    if body and all(body.get(k) for k in ("age", "gender", "height_cm", "weight_kg", "activity_level")):
        tdee = calculate_tdee(body["age"], body["gender"], body["height_cm"], body["weight_kg"], body["activity_level"])

    macro = None
    if tdee is not None:
        goal_type = (profile.get("goal") or {}).get("goal_type")
        macro = suggest_nutrition_target(tdee, goal_type, profile.get("health_conditions", []),
                                                 profile.get("health_notes"))
    structure = suggest_meal_structure(profile)

    applied = False
    if apply and macro is not None:
        _persist_nutrition_target(session, user_id, macro)
        applied = True

    return {
        "tdee_kcal": tdee,
        "nutrition_target": macro.model_dump() if macro else None,
        "meal_structure": structure.model_dump(),
        "applied": applied,
        "missing_body_metrics": tdee is None,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Setup resolution for the generation gate (consult-or-AI) + backfill
# ═══════════════════════════════════════════════════════════════════════════

def _activate_one(session: Session, user_id: uuid.UUID, model, obj) -> None:
    """Deactivate the user's current active row of `model`, then activate `obj`.
    Flush between so the partial unique index never sees two active rows."""
    for ex in session.exec(select(model).where(
        model.created_for == user_id, model.active == True)).all():  # noqa: E712
        if ex.id != obj.id:
            ex.active = False
            session.add(ex)
    session.flush()
    obj.active = True
    session.add(obj)
    session.flush()


def _create_inactive_setup(session: Session, user_id: uuid.UUID, profile: dict, tdee: int):
    goal_type = (profile.get("goal") or {}).get("goal_type")
    macro = suggest_nutrition_target(
        tdee, goal_type, profile.get("health_conditions", []), profile.get("health_notes")
    )
    target = NutritionTarget(
        created_for=user_id, created_by=user_id, active=False,
        calories_kcal=macro.calories_kcal, protein_g=macro.protein_g,
        carbs_g=macro.carbs_g, fat_g=macro.fat_g,
    )
    structure = suggest_meal_structure(profile)
    setting = MealPlanSetting(
        created_for=user_id, created_by=user_id, active=False,
        name="AI Suggested Plan", timed_meals_per_day=structure.timed_meals_per_day,
    )
    session.add_all([target, setting])
    session.flush()
    for slot in structure.slots:
        session.add(MealPlanSettingTimedMeal(
            meal_plan_setting_id=setting.id, name=slot.name,
            meal_time=_coerce_meal_time(slot.meal_time),  # normalize to the enum
            calories_pct=slot.calories_pct,
        ))
    session.flush()
    return target, setting


def resolve_setup(session: Session, user_id: uuid.UUID, choice: str, approve: bool = False) -> dict:
    """Called when the generation gate reports `needs_setup`.
    - 'consultation': raise a referral notification (a consultant will set it up).
    - 'ai_generate': create INACTIVE target+setting drafts; if approve → activate
      (explicit) and generate today's plan."""
    if choice == "consultation":
        notif_service.create(
            session, user_id, NotificationType.consult_referral,
            title="Book a consultation",
            body="A consultant can set up your nutrition target and meal plan.",
            commit=True,
        )
        return {"status": "consultation_suggested"}

    if choice != "ai_generate":
        raise HTTPException(400, "choice must be 'ai_generate' or 'consultation'")

    profile = assemble_profile(session, user_id)
    body = profile.get("body")
    if not body or not all(body.get(k) for k in ("age", "gender", "height_cm", "weight_kg", "activity_level")):
        raise HTTPException(400, "Complete your body metrics (age, gender, height, weight, activity) first")
    tdee = calculate_tdee(body["age"], body["gender"], body["height_cm"], body["weight_kg"], body["activity_level"])

    target, setting = _create_inactive_setup(session, user_id, profile, tdee)

    if not approve:
        session.commit()
        return {
            "status": "drafts_created",
            "approve_required": True,
            "nutrition_target": {"id": str(target.id), "calories_kcal": target.calories_kcal,
                                 "protein_g": target.protein_g, "carbs_g": target.carbs_g, "fat_g": target.fat_g},
            "meal_setting": {"id": str(setting.id), "name": setting.name,
                             "timed_meals_per_day": setting.timed_meals_per_day},
        }

    _activate_one(session, user_id, NutritionTarget, target)
    _activate_one(session, user_id, MealPlanSetting, setting)
    session.commit()
    plan = generate_day_plan(session, user_id, date.today().weekday())
    return {"status": "generated", "plan": plan}


# ═══════════════════════════════════════════════════════════════════════════
# Delete (no DB cascade — remove children bottom-up)
# ═══════════════════════════════════════════════════════════════════════════

def _delete_timed_meal_cascade(session: Session, tm: TimedMeal) -> None:
    """Delete one slot and everything under it: its combo options, the combos those
    options point to (each MealCombo is created fresh per option, so single-owner),
    and the combos' items. Order avoids FK violations (TimedMeal.meal_combo_id)."""
    options = session.exec(
        select(TimedMealComboOption).where(TimedMealComboOption.timed_meal_id == tm.id)
    ).all()
    combo_ids = [opt.meal_combo_id for opt in options]

    for opt in options:
        session.delete(opt)
    session.delete(tm)          # clears the tm.meal_combo_id FK reference
    session.flush()

    for combo_id in combo_ids:
        for ci in session.exec(
            select(MealComboItem).where(MealComboItem.meal_combo_id == combo_id)
        ).all():
            session.delete(ci)
        combo = session.get(MealCombo, combo_id)
        if combo:
            session.delete(combo)
    session.flush()


def _authorize_timed_meal(session: Session, user_id: uuid.UUID, timed_meal_id: uuid.UUID) -> TimedMeal:
    tm = session.get(TimedMeal, timed_meal_id)
    if not tm:
        raise HTTPException(404, "Timed meal not found")
    day_plan = session.get(DayMealPlan, tm.day_plan_id)
    if not day_plan:
        raise HTTPException(404, "Day plan not found")
    week_plan = session.get(WeekMealPlan, day_plan.week_plan_id)
    if not week_plan or week_plan.user_id != user_id:
        raise HTTPException(403, "Not authorized")
    return tm


def _authorize_day_plan(session: Session, user_id: uuid.UUID, day_plan_id: uuid.UUID) -> DayMealPlan:
    day_plan = session.get(DayMealPlan, day_plan_id)
    if not day_plan:
        raise HTTPException(404, "Day plan not found")
    week_plan = session.get(WeekMealPlan, day_plan.week_plan_id)
    if not week_plan or week_plan.user_id != user_id:
        raise HTTPException(403, "Not authorized")
    return day_plan


def _authorize_week_plan(session: Session, user_id: uuid.UUID, week_plan_id: uuid.UUID) -> WeekMealPlan:
    week_plan = session.get(WeekMealPlan, week_plan_id)
    if not week_plan or week_plan.user_id != user_id:
        raise HTTPException(403, "Not authorized")
    return week_plan


def delete_timed_meal(session: Session, user_id: uuid.UUID, timed_meal_id: uuid.UUID) -> dict:
    tm = _authorize_timed_meal(session, user_id, timed_meal_id)
    _delete_timed_meal_cascade(session, tm)
    session.commit()
    return {"message": "Timed meal deleted"}


def delete_day_plan(session: Session, user_id: uuid.UUID, day_plan_id: uuid.UUID) -> dict:
    day_plan = _authorize_day_plan(session, user_id, day_plan_id)
    week_plan_id = day_plan.week_plan_id
    for tm in list(day_plan.timed_meals):
        _delete_timed_meal_cascade(session, tm)
    session.delete(day_plan)
    session.flush()

    # Drop the week too if it now has no remaining days.
    remaining = session.exec(
        select(DayMealPlan).where(DayMealPlan.week_plan_id == week_plan_id)
    ).first()
    week_deleted = False
    if not remaining:
        week = session.get(WeekMealPlan, week_plan_id)
        if week:
            session.delete(week)
            week_deleted = True
    session.commit()
    return {"message": "Day plan deleted", "week_deleted": week_deleted}


def delete_week_plan(session: Session, user_id: uuid.UUID, week_plan_id: uuid.UUID) -> dict:
    week_plan = _authorize_week_plan(session, user_id, week_plan_id)
    for day_plan in list(week_plan.day_plans):
        for tm in list(day_plan.timed_meals):
            _delete_timed_meal_cascade(session, tm)
        session.delete(day_plan)
    session.flush()
    session.delete(week_plan)
    session.commit()
    return {"message": "Week plan deleted"}


# ═══════════════════════════════════════════════════════════════════════════
# Swap + read (kept from the previous generator)
# ═══════════════════════════════════════════════════════════════════════════

def swap_chosen_combo(session: Session, user_id: uuid.UUID, timed_meal_id: uuid.UUID,
                      combo_option_id: uuid.UUID) -> dict:
    timed_meal = session.get(TimedMeal, timed_meal_id)
    if not timed_meal:
        raise HTTPException(404, "Timed meal not found")
    day_plan = session.get(DayMealPlan, timed_meal.day_plan_id)
    if not day_plan:
        raise HTTPException(404, "Day plan not found")
    week_plan = session.get(WeekMealPlan, day_plan.week_plan_id)
    if not week_plan or week_plan.user_id != user_id:
        raise HTTPException(403, "Not authorized")

    new_option = session.get(TimedMealComboOption, combo_option_id)
    if not new_option or new_option.timed_meal_id != timed_meal_id:
        raise HTTPException(404, "Combo option not found for this timed meal")

    for opt in session.exec(
        select(TimedMealComboOption).where(
            TimedMealComboOption.timed_meal_id == timed_meal_id,
            TimedMealComboOption.is_chosen == True)  # noqa: E712
    ).all():
        opt.is_chosen = False
        session.add(opt)

    new_option.is_chosen = True
    session.add(new_option)

    new_combo = session.get(MealCombo, new_option.meal_combo_id)
    timed_meal.meal_combo_id = new_option.meal_combo_id
    if new_combo:
        timed_meal.calories = new_combo.calories
        timed_meal.protein_g = new_combo.protein_g
        timed_meal.carbs_g = new_combo.carbs_g
        timed_meal.fat_g = new_combo.fat_g
    timed_meal.updated_at = utc_now()
    session.add(timed_meal)
    session.commit()
    return {"message": "Combo swapped successfully", "new_combo_id": str(new_option.meal_combo_id)}


def get_user_plans(session: Session, user_id: uuid.UUID) -> List[Dict[str, Any]]:
    """Get all week plans for a user with nested day plans and timed meals."""
    week_plans = session.exec(
        select(WeekMealPlan)
        .where(WeekMealPlan.user_id == user_id)
        .order_by(WeekMealPlan.created_at.desc())
    ).all()

    if not week_plans:
        return []

    wp_ids = [wp.id for wp in week_plans]
    day_plans = session.exec(select(DayMealPlan).where(DayMealPlan.week_plan_id.in_(wp_ids))).all()
    
    dp_ids = [dp.id for dp in day_plans]
    timed_meals = []
    if dp_ids:
        timed_meals = session.exec(select(TimedMeal).where(TimedMeal.day_plan_id.in_(dp_ids))).all()
        
    tm_ids = [tm.id for tm in timed_meals]
    options = []
    if tm_ids:
        options = session.exec(select(TimedMealComboOption).where(TimedMealComboOption.timed_meal_id.in_(tm_ids))).all()
        
    combo_ids = list({opt.meal_combo_id for opt in options})
    combos = []
    if combo_ids:
        combos = session.exec(select(MealCombo).where(MealCombo.id.in_(combo_ids))).all()
        
    combo_items = []
    if combo_ids:
        combo_items = session.exec(select(MealComboItem).where(MealComboItem.meal_combo_id.in_(combo_ids))).all()
        
    meal_ids = list({ci.meal_id for ci in combo_items})
    meals = []
    if meal_ids:
        meals = session.exec(select(Meal).where(Meal.id.in_(meal_ids))).all()

    # Build dictionaries for fast lookup
    dp_by_wp = {wp.id: [] for wp in week_plans}
    for dp in day_plans:
        dp_by_wp[dp.week_plan_id].append(dp)
        
    tm_by_dp = {dp.id: [] for dp in day_plans}
    for tm in timed_meals:
        tm_by_dp[tm.day_plan_id].append(tm)
        
    opt_by_tm = {tm.id: [] for tm in timed_meals}
    for opt in options:
        opt_by_tm[opt.timed_meal_id].append(opt)
    for tm_id in opt_by_tm:
        opt_by_tm[tm_id].sort(key=lambda o: o.rank)
        
    combo_by_id = {c.id: c for c in combos}
    meal_by_id = {m.id: m for m in meals}
    
    ci_by_combo = {c.id: [] for c in combos}
    for ci in combo_items:
        ci_by_combo[ci.meal_combo_id].append(ci)

    results = []
    for wp in week_plans:
        days = []
        for dp in dp_by_wp[wp.id]:
            tms = []
            for tm in tm_by_dp[dp.id]:
                option_data = []
                chosen_extra = {"sodium_mg": 0.0, "fiber_g": 0.0, "sugar_g": 0.0}
                for opt in opt_by_tm[tm.id]:
                    combo = combo_by_id.get(opt.meal_combo_id)
                    combo_items_list = []
                    
                    extra = {"sodium_mg": 0.0, "fiber_g": 0.0, "sugar_g": 0.0}
                    if combo:
                        for ci in ci_by_combo.get(combo.id, []):
                            meal = meal_by_id.get(ci.meal_id)
                            sodium = (meal.sodium_mg or 0) * ci.quantity if meal else 0
                            fiber = (meal.fiber_g or 0) * ci.quantity if meal else 0
                            sugar = (meal.sugar_g or 0) * ci.quantity if meal else 0
                            extra["sodium_mg"] += sodium
                            extra["fiber_g"] += fiber
                            extra["sugar_g"] += sugar
                            
                            combo_items_list.append({
                                "meal_id": str(ci.meal_id),
                                "meal_name": meal.name if meal else "Unknown",
                                "meal_image_url": meal.image_url if meal else None,
                                "servings": ci.quantity,
                                "calories": meal.calories * ci.quantity if meal else 0,
                                "protein_g": meal.protein_g * ci.quantity if meal else 0,
                                "carbs_g": meal.carbs_g * ci.quantity if meal else 0,
                                "fat_g": meal.fat_g * ci.quantity if meal else 0,
                                "sodium_mg": round(sodium, 1),
                                "fiber_g": round(fiber, 1),
                                "sugar_g": round(sugar, 1),
                            })
                    extra = {k: round(v, 1) for k, v in extra.items()}
                    if opt.is_chosen:
                        chosen_extra = extra
                    option_data.append({
                        "option_id": str(opt.id), "combo_id": str(opt.meal_combo_id),
                        "combo_name": combo.name if combo else "", "rank": opt.rank,
                        "is_chosen": opt.is_chosen,
                        "macros": {
                            "calories": combo.calories if combo else 0,
                            "protein_g": combo.protein_g if combo else 0,
                            "carbs_g": combo.carbs_g if combo else 0,
                            "fat_g": combo.fat_g if combo else 0,
                            **extra,
                        },
                        "meals": combo_items_list,
                    })
                tms.append({
                    "timed_meal_id": str(tm.id),
                    "meal_time": tm.meal_time.value if hasattr(tm.meal_time, "value") else str(tm.meal_time),
                    "macros": {"calories": tm.calories, "protein_g": tm.protein_g,
                               "carbs_g": tm.carbs_g, "fat_g": tm.fat_g, **chosen_extra},
                    "combo_options": option_data,
                })
            days.append({"day_plan_id": str(dp.id), "day_of_week": dp.day_of_week, "timed_meals": tms})
        results.append({
            "week_plan_id": str(wp.id), "title": wp.title,
            "status": wp.status.value if hasattr(wp.status, "value") else str(wp.status),
            "days": sorted(days, key=lambda d: d["day_of_week"]),
        })
    return results
