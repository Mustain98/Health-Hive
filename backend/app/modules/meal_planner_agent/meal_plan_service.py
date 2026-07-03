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
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException
from sqlmodel import Session, select

from app.modules.meal.models import (
    FoodItem,
    Meal,
    MealCombo,
    MealComboItem,
    MealLabelName,
    MealTimeType,
    TimedMeal,
    TimedMealComboOption,
    MealPlanSetting,
    DayMealPlan,
    LikedMeal,
    WeekMealPlan,
)
from app.modules.user.models import (
    NutritionTarget,
    UserData,
    UserGoal,
    UserAllergen,
    UserPreference,
    UserHealthProfile,
)
from app.utils.time import utc_now
from app.utils.calculate import calculate_tdee
from app.modules.meal_planner_agent import embeddings as emb
from app.modules.meal_planner_agent import enrichment as enr
from app.modules.meal_planner_agent import llm as llm_mod

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
    v = (value or "").lower()
    return MealTimeType(v) if v in _VALID_MEAL_TIMES else MealTimeType.lunch


# ═══════════════════════════════════════════════════════════════════════════
# Profile + macro target
# ═══════════════════════════════════════════════════════════════════════════

def _active_target(session: Session, user_id: uuid.UUID) -> Optional[NutritionTarget]:
    return session.exec(
        select(NutritionTarget)
        .where(NutritionTarget.created_for == user_id, NutritionTarget.active == True)  # noqa: E712
    ).first()


def _active_goal(session: Session, user_id: uuid.UUID) -> Optional[UserGoal]:
    return session.exec(
        select(UserGoal).where(UserGoal.created_for == user_id, UserGoal.active == True)  # noqa: E712
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


def resolve_macro_target(session: Session, user_id: uuid.UUID, macro_source: str, profile: dict) -> Dict[str, float]:
    """macro_source: 'current' uses the active NutritionTarget (400 if none);
    'auto' computes TDEE + LLM suggestion and persists it as the active target."""
    if macro_source == "auto":
        body = profile.get("body")
        if not body or not all(body.get(k) for k in ("age", "gender", "height_cm", "weight_kg", "activity_level")):
            raise HTTPException(400, "Complete your body metrics (age, gender, height, weight, activity) to auto-generate")
        tdee = calculate_tdee(body["age"], body["gender"], body["height_cm"], body["weight_kg"], body["activity_level"])
        goal_type = (profile.get("goal") or {}).get("goal_type")
        suggestion = llm_mod.suggest_nutrition_target(
            tdee, goal_type, profile.get("health_conditions", []), profile.get("health_notes")
        )
        target = _persist_nutrition_target(session, user_id, suggestion)
    else:
        target = _active_target(session, user_id)
        if not target:
            raise HTTPException(400, "No nutrition target — get an AI suggestion or set one")

    return {
        "calories": float(target.calories_kcal),
        "protein_g": float(target.protein_g),
        "carbs_g": float(target.carbs_g),
        "fat_g": float(target.fat_g),
    }


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


def build_pool(session: Session, user_id: uuid.UUID, constraint, ctx: dict) -> List[Dict[str, Any]]:
    """Retrieve top meals for the constraint's query, apply hard allergen/diet filters, add like boosts."""
    meal_ids = emb.retrieve_meal_ids(session, constraint.retrieval_query, k=POOL_K)
    if not meal_ids:
        return []
    meals = session.exec(select(Meal).where(Meal.id.in_(meal_ids))).all()
    order = {mid: i for i, mid in enumerate(meal_ids)}
    meals.sort(key=lambda m: order.get(m.id, 999))

    allergen_ids: set = ctx["allergen_food_ids"]
    disallowed_labels: set = ctx["disallowed_food_labels"]
    liked_food_ids: set = ctx["liked_food_ids"]
    liked_meal_ids: set = ctx["liked_meal_ids"]

    pool: List[Dict[str, Any]] = []
    for meal in meals:
        ingredient_fi_ids = {mfi.food_item_id for mfi in meal.meal_food_items}
        # hard: allergen exclusion
        if ingredient_fi_ids & allergen_ids:
            continue
        # hard: diet-preference exclusion via ingredient food-item labels
        if disallowed_labels:
            ing_labels: set = set()
            for mfi in meal.meal_food_items:
                if mfi.food_item:
                    for lbl in mfi.food_item.labels:
                        ing_labels.add(lbl.name.value if hasattr(lbl.name, "value") else str(lbl.name))
            if ing_labels & disallowed_labels:
                continue

        meal_label_names = [l.name.value if hasattr(l.name, "value") else str(l.name) for l in meal.labels]
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

def _compute_context(session: Session, user_id: uuid.UUID, macro_source: str) -> dict:
    """Everything computed once per generation and reused across days."""
    enr.ensure_meal_enrichment(session)   # estimate nutrients + health context (cached)
    emb.ensure_meal_embeddings(session)   # embed enriched text (cached)
    profile = assemble_profile(session, user_id)
    macro_target = resolve_macro_target(session, user_id, macro_source, profile)
    setting = _active_setting(session, user_id)
    slots = _setting_slots(setting)
    plan = llm_mod.generate_constraints(
        profile, macro_target, slots, allowed_labels=[m.value for m in MealLabelName]
    )

    ctx = _retrieval_ctx(session, user_id, profile)
    pools = [build_pool(session, user_id, c, ctx) for c in plan.slots]
    return {"macro_target": macro_target, "constraints": plan.slots, "pools": pools}


def _generate_timed_meal(session: Session, timed_meal: TimedMeal, constraint, pool, day_index: int) -> dict:
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
    chosen_rank = (day_index % len(chosen_selections)) + 1  # rotate chosen per day for variety
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


def _build_day(session: Session, user_id: uuid.UUID, plan_date: date, ctx: dict,
               day_index: int, week_plan_id: Optional[uuid.UUID] = None) -> dict:
    if week_plan_id:
        existing_day = session.exec(
            select(DayMealPlan).where(
                DayMealPlan.week_plan_id == week_plan_id, DayMealPlan.plan_date == plan_date)
        ).first()
    else:
        existing_day = None

    if existing_day:
        day_plan = existing_day
    else:
        if not week_plan_id:
            wp = WeekMealPlan(title=f"Plan for {plan_date}", start_date=plan_date, end_date=plan_date,
                              user_id=user_id, status="active")
            session.add(wp)
            session.flush()
            week_plan_id = wp.id
        day_plan = DayMealPlan(week_plan_id=week_plan_id, plan_date=plan_date)
        session.add(day_plan)
        session.flush()

    results = []
    for slot_idx, constraint in enumerate(ctx["constraints"]):
        timed_meal = TimedMeal(day_plan_id=day_plan.id, meal_time=_coerce_meal_time(constraint.meal_time))
        session.add(timed_meal)
        session.flush()
        results.append(_generate_timed_meal(session, timed_meal, constraint, ctx["pools"][slot_idx], day_index))

    return {"day_plan_id": str(day_plan.id), "plan_date": str(plan_date), "timed_meals": results}


def generate_day_plan(session: Session, user_id: uuid.UUID, plan_date: date,
                      macro_source: str = "current", week_plan_id: Optional[uuid.UUID] = None) -> dict:
    ctx = _compute_context(session, user_id, macro_source)
    result = _build_day(session, user_id, plan_date, ctx, day_index=0, week_plan_id=week_plan_id)
    session.commit()
    return result


def generate_week_plan(session: Session, user_id: uuid.UUID, start_date: date,
                       macro_source: str = "current") -> dict:
    end_date = start_date + timedelta(days=6)
    ctx = _compute_context(session, user_id, macro_source)  # constraints + pools computed once

    week_plan = WeekMealPlan(title=f"Week Plan {start_date} - {end_date}", start_date=start_date,
                             end_date=end_date, user_id=user_id, status="active")
    session.add(week_plan)
    session.flush()

    day_results = []
    for day_offset in range(7):
        current_date = start_date + timedelta(days=day_offset)
        day_results.append(_build_day(session, user_id, current_date, ctx, day_index=day_offset,
                                      week_plan_id=week_plan.id))

    session.commit()
    return {"week_plan_id": str(week_plan.id), "start_date": str(start_date),
            "end_date": str(end_date), "days": day_results}


def regenerate_timed_meal(session: Session, user_id: uuid.UUID, timed_meal_id: uuid.UUID) -> dict:
    timed_meal = session.get(TimedMeal, timed_meal_id)
    if not timed_meal:
        raise HTTPException(404, "Timed meal not found")
    day_plan = session.get(DayMealPlan, timed_meal.day_plan_id)
    if not day_plan:
        raise HTTPException(404, "Day plan not found")
    week_plan = session.get(WeekMealPlan, day_plan.week_plan_id)
    if not week_plan or week_plan.user_id != user_id:
        raise HTTPException(403, "Not authorized")

    ctx = _compute_context(session, user_id, "current")
    meal_time_val = timed_meal.meal_time.value if hasattr(timed_meal.meal_time, "value") else str(timed_meal.meal_time)
    idx = next((i for i, c in enumerate(ctx["constraints"]) if _coerce_meal_time(c.meal_time).value == meal_time_val), 0)
    result = _generate_timed_meal(session, timed_meal, ctx["constraints"][idx], ctx["pools"][idx], day_index=0)
    session.commit()
    return result


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
        macro = llm_mod.suggest_nutrition_target(tdee, goal_type, profile.get("health_conditions", []),
                                                 profile.get("health_notes"))
    structure = llm_mod.suggest_meal_structure(profile)

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
    week_plans = session.exec(
        select(WeekMealPlan).where(WeekMealPlan.user_id == user_id).order_by(WeekMealPlan.start_date.desc())
    ).all()

    results = []
    for wp in week_plans:
        days = []
        for dp in wp.day_plans:
            tms = []
            for tm in dp.timed_meals:
                options = session.exec(
                    select(TimedMealComboOption)
                    .where(TimedMealComboOption.timed_meal_id == tm.id)
                    .order_by(TimedMealComboOption.rank)
                ).all()
                option_data = []
                for opt in options:
                    combo = session.get(MealCombo, opt.meal_combo_id)
                    combo_items = []
                    if combo:
                        for ci in combo.combo_items:
                            meal = session.get(Meal, ci.meal_id)
                            combo_items.append({
                                "meal_id": str(ci.meal_id),
                                "meal_name": meal.name if meal else "Unknown",
                                "meal_image_url": meal.image_url if meal else None,
                                "servings": ci.quantity,
                                "calories": meal.calories * ci.quantity if meal else 0,
                                "protein_g": meal.protein_g * ci.quantity if meal else 0,
                                "carbs_g": meal.carbs_g * ci.quantity if meal else 0,
                                "fat_g": meal.fat_g * ci.quantity if meal else 0,
                            })
                    option_data.append({
                        "option_id": str(opt.id), "combo_id": str(opt.meal_combo_id),
                        "combo_name": combo.name if combo else "", "rank": opt.rank,
                        "is_chosen": opt.is_chosen,
                        "macros": {
                            "calories": combo.calories if combo else 0,
                            "protein_g": combo.protein_g if combo else 0,
                            "carbs_g": combo.carbs_g if combo else 0,
                            "fat_g": combo.fat_g if combo else 0,
                        },
                        "meals": combo_items,
                    })
                tms.append({
                    "timed_meal_id": str(tm.id),
                    "meal_time": tm.meal_time.value if hasattr(tm.meal_time, "value") else str(tm.meal_time),
                    "macros": {"calories": tm.calories, "protein_g": tm.protein_g,
                               "carbs_g": tm.carbs_g, "fat_g": tm.fat_g},
                    "combo_options": option_data,
                })
            days.append({"day_plan_id": str(dp.id), "plan_date": str(dp.plan_date), "timed_meals": tms})
        results.append({
            "week_plan_id": str(wp.id), "title": wp.title, "start_date": str(wp.start_date),
            "end_date": str(wp.end_date),
            "status": wp.status.value if hasattr(wp.status, "value") else str(wp.status),
            "days": sorted(days, key=lambda d: d["plan_date"]),
        })
    return results
