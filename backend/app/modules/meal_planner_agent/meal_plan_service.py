"""
meal_plan_service.py — AI-powered meal plan generation.

Generates personalized MealCombos for each TimedMeal by:
1. Building a filtered meal pool (labels, allergens, preferences)
2. Generating ~20 candidate combos with serving adjustments
3. Asking Groq to pick the best 5
4. Persisting the results
"""
import json
import math
import os
import random
import re
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from groq import Groq
from sqlmodel import Session, select

from app.modules.meal.models import FoodItem
from app.modules.meal.models import (
    Meal,
    MealCombo,
    MealComboItem,
    MealFoodItem,
    MealLabel,
    MealLabelLink,
    MealLabelName,
    MealTimeType,
    TimedMeal,
    TimedMealComboOption,
)
from app.modules.meal.models import (
    MealPlanSetting,
    MealPlanSettingTimedMeal,
)
from app.modules.meal.models import DayMealPlan, LikedMeal, WeekMealPlan
from app.modules.user.models import NutritionTarget
from app.modules.user.models import UserAllergen, UserPreference
from app.utils.time import utc_now


GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SERVING_CAP = 3.0
SERVING_MIN = 1.0
MACRO_TOLERANCE = 0.10  # ±10%
CANDIDATE_COUNT = 20
COMBO_PICK_COUNT = 5


# ═══════════════════════════════════════════════════════════════════════════════
# 1. MEAL POOL BUILDER
# ═══════════════════════════════════════════════════════════════════════════════

def _get_meal_label_ids(session: Session, label_names: List[str]) -> List[uuid.UUID]:
    """Resolve MealLabelName strings → MealLabel.id list."""
    stmt = select(MealLabel).where(MealLabel.name.in_(label_names))  # type: ignore[arg-type]
    labels = session.exec(stmt).all()
    return [lbl.id for lbl in labels]


def _get_allergen_food_item_ids(session: Session, user_id: uuid.UUID) -> set:
    """Get set of food_item_ids the user is allergic to."""
    stmt = select(UserAllergen.food_item_id).where(UserAllergen.user_id == user_id)
    return set(session.exec(stmt).all())


def _get_liked_food_item_ids(session: Session, user_id: uuid.UUID) -> set:
    """Get set of food_item_ids the user prefers."""
    stmt = select(UserPreference.food_item_id).where(UserPreference.user_id == user_id)
    return set(session.exec(stmt).all())


def _get_liked_meal_ids(session: Session, user_id: uuid.UUID) -> set:
    """Get set of meal_ids the user has liked."""
    stmt = select(LikedMeal.meal_id).where(LikedMeal.user_id == user_id)
    return set(session.exec(stmt).all())


def build_meal_pool(
    session: Session,
    user_id: uuid.UUID,
    meal_labels: List[str],
) -> List[Dict[str, Any]]:
    """
    Build a scored pool of meals for a timed-meal slot.

    Returns list of dicts:
      { "meal": Meal, "labels": [str], "ingredient_fi_ids": set, "score": int }
    """
    # 1. Fetch all verified meals (eager-load labels + food items)
    all_meals = session.exec(select(Meal).where(Meal.is_verified == True)).all()

    # Build lookup structures
    allergen_fi_ids = _get_allergen_food_item_ids(session, user_id)
    liked_fi_ids = _get_liked_food_item_ids(session, user_id)
    liked_meal_ids = _get_liked_meal_ids(session, user_id)

    pool: List[Dict[str, Any]] = []

    for meal in all_meals:
        # Resolve labels
        meal_label_names = [lbl.name.value if hasattr(lbl.name, "value") else lbl.name for lbl in meal.labels]

        # Filter: must contain at least one of the timed-meal labels
        if meal_labels:
            if not any(ml in meal_label_names for ml in meal_labels):
                continue

        # Resolve ingredient food_item_ids
        ingredient_fi_ids = set()
        for mfi in meal.meal_food_items:
            ingredient_fi_ids.add(mfi.food_item_id)

        # Exclude meals containing any allergen
        if ingredient_fi_ids & allergen_fi_ids:
            continue

        # Score: boost if meal liked or contains liked food items
        score = 0
        if meal.id in liked_meal_ids:
            score += 3
        liked_overlap = ingredient_fi_ids & liked_fi_ids
        score += len(liked_overlap)

        pool.append({
            "meal": meal,
            "labels": meal_label_names,
            "ingredient_fi_ids": ingredient_fi_ids,
            "score": score,
        })

    # Sort by score descending (liked items first)
    pool.sort(key=lambda x: x["score"], reverse=True)
    return pool


# ═══════════════════════════════════════════════════════════════════════════════
# 2. CANDIDATE COMBO GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

def _categorize_pool(pool: List[Dict]) -> Tuple[List, List, List]:
    """Split pool into mains, sides, desserts."""
    mains, sides, desserts = [], [], []
    for entry in pool:
        lbls = entry["labels"]
        if "main_meal" in lbls:
            mains.append(entry)
        elif "side_meal" in lbls:
            sides.append(entry)
        elif "dessert" in lbls:
            desserts.append(entry)
        else:
            mains.append(entry)  # default: treat as main
    return mains, sides, desserts


def _calc_combo_macros(meals_with_servings: List[Tuple[Meal, float]]) -> Dict[str, float]:
    """Calculate total macros for a combo given (meal, servings) pairs."""
    total = {"calories": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0}
    for meal, servings in meals_with_servings:
        total["calories"] += meal.calories * servings
        total["protein_g"] += meal.protein_g * servings
        total["carbs_g"] += meal.carbs_g * servings
        total["fat_g"] += meal.fat_g * servings
    return {k: round(v, 1) for k, v in total.items()}


def _within_tolerance(actual: Dict[str, float], target: Dict[str, float]) -> bool:
    """Check if all macros are within ±MACRO_TOLERANCE of target."""
    for key in ["calories", "protein_g", "carbs_g", "fat_g"]:
        t = target.get(key, 0)
        if t == 0:
            continue
        if abs(actual[key] - t) / t > MACRO_TOLERANCE:
            return False
    return True


def _adjust_servings(
    combo_meals: List[Meal],
    target: Dict[str, float],
) -> List[Tuple[Meal, float]]:
    """
    Adjust serving multiplier for the combo to meet target macros.
    The primary meal drives the scale, sides/desserts get 1 serving.
    """
    if not combo_meals:
        return []

    main_meal = combo_meals[0]
    other_meals = combo_meals[1:]

    # Fixed serving for sides/desserts
    fixed_cals = sum(m.calories for m in other_meals)
    remaining_target = max(target.get("calories", 0) - fixed_cals, 0)

    if main_meal.calories > 0:
        scale = remaining_target / main_meal.calories
    else:
        scale = 1.0

    scale = max(SERVING_MIN, min(SERVING_CAP, round(scale, 1)))

    result = [(main_meal, scale)]
    for m in other_meals:
        result.append((m, 1.0))

    return result


def generate_candidate_combos(
    pool: List[Dict[str, Any]],
    target_macros: Dict[str, float],
    timed_meal_labels: List[str],
    count: int = CANDIDATE_COUNT,
) -> List[Dict[str, Any]]:
    """
    Generate ~count candidate combos from the pool.
    Each combo: 1 main + optionally side + optionally dessert.
    Servings adjusted to approach target macros.
    """
    mains, sides, desserts = _categorize_pool(pool)

    if not mains:
        return []

    candidates = []
    attempts = 0
    max_attempts = count * 5  # avoid infinite loop

    while len(candidates) < count and attempts < max_attempts:
        attempts += 1

        # Pick 1 main (weighted by score)
        weights_main = [max(e["score"] + 1, 1) for e in mains]
        main_entry = random.choices(mains, weights=weights_main, k=1)[0]
        combo_meals = [main_entry["meal"]]
        combo_labels = set(main_entry["labels"])

        # Optionally add side (60% chance or if labels require it)
        need_side = "side_meal" in timed_meal_labels
        if sides and (need_side or random.random() < 0.6):
            side_entry = random.choice(sides)
            combo_meals.append(side_entry["meal"])
            combo_labels.update(side_entry["labels"])

        # Optionally add dessert (30% chance or if labels require it)
        need_dessert = "dessert" in timed_meal_labels
        if desserts and (need_dessert or random.random() < 0.3):
            dessert_entry = random.choice(desserts)
            combo_meals.append(dessert_entry["meal"])
            combo_labels.update(dessert_entry["labels"])

        # Adjust servings
        meals_with_servings = _adjust_servings(combo_meals, target_macros)
        macros = _calc_combo_macros(meals_with_servings)

        # Only include if roughly viable (within 20% — Groq will fine-tune later)
        cal_target = target_macros.get("calories", 0)
        if cal_target > 0 and abs(macros["calories"] - cal_target) / cal_target > 0.25:
            continue

        # Avoid exact duplicate combos
        combo_key = tuple(sorted(m.id for m in combo_meals))
        if any(c["key"] == combo_key for c in candidates):
            continue

        candidates.append({
            "key": combo_key,
            "meals": meals_with_servings,
            "macros": macros,
            "labels": list(combo_labels),
        })

    return candidates


# ═══════════════════════════════════════════════════════════════════════════════
# 3. GROQ SELECTION
# ═══════════════════════════════════════════════════════════════════════════════

GROQ_SYSTEM_PROMPT = """You are a professional meal planning AI assistant.
Given a list of candidate meal combos with their nutrition totals and the user's
target macros for this particular meal slot, select the best 5 combos.

Prioritize:
- Variety between the 5 selections (different main dishes)
- Closeness to the target macros (within ±10%)
- Nutritional balance and appeal

Respond with ONLY a JSON array of 5 combo indices (0-based).
Example: [0, 3, 7, 12, 18]
Do NOT add any explanation or markdown."""


def select_best_combos_via_groq(
    candidates: List[Dict[str, Any]],
    target_macros: Dict[str, float],
) -> List[int]:
    """
    Send candidates to Groq and get back 5 best indices.
    Falls back to top-5 by calorie closeness if Groq fails.
    """
    if len(candidates) <= COMBO_PICK_COUNT:
        return list(range(len(candidates)))

    # Build concise combo descriptions for the prompt
    combo_descriptions = []
    for i, c in enumerate(candidates):
        meal_names = [f"{m.name} (×{s})" for m, s in c["meals"]]
        combo_descriptions.append({
            "index": i,
            "meals": meal_names,
            "macros": c["macros"],
        })

    user_msg = (
        f"Target macros: {json.dumps(target_macros)}\n\n"
        f"Candidates:\n{json.dumps(combo_descriptions, indent=1)}\n\n"
        f"Select the best 5 indices."
    )

    try:
        if not GROQ_API_KEY:
            raise ValueError("No GROQ_API_KEY")

        client = Groq(api_key=GROQ_API_KEY)
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": GROQ_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.3,
        )
        raw = response.choices[0].message.content.strip()
        # Strip markdown code blocks if present
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned).strip()

        indices = json.loads(cleaned)
        if isinstance(indices, list) and len(indices) >= COMBO_PICK_COUNT:
            valid = [i for i in indices[:COMBO_PICK_COUNT] if 0 <= i < len(candidates)]
            if len(valid) == COMBO_PICK_COUNT:
                return valid
    except Exception as e:
        print(f"[MealPlan] Groq selection failed, using fallback: {e}")

    # Fallback: pick top 5 closest to target calories
    cal_target = target_macros.get("calories", 0)
    sorted_idx = sorted(
        range(len(candidates)),
        key=lambda i: abs(candidates[i]["macros"]["calories"] - cal_target),
    )
    return sorted_idx[:COMBO_PICK_COUNT]


# ═══════════════════════════════════════════════════════════════════════════════
# 4. PERSISTENCE HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _persist_combo(
    session: Session,
    meals_with_servings: List[Tuple[Meal, float]],
    macros: Dict[str, float],
    meal_time: MealTimeType,
    name: str,
) -> MealCombo:
    """Create a MealCombo + MealComboItem rows and return the combo."""
    combo = MealCombo(
        name=name,
        meal_time=meal_time,
        calories=macros["calories"],
        protein_g=macros["protein_g"],
        carbs_g=macros["carbs_g"],
        fat_g=macros["fat_g"],
    )
    session.add(combo)
    session.flush()

    for meal, servings in meals_with_servings:
        item = MealComboItem(
            meal_combo_id=combo.id,
            meal_id=meal.id,
            quantity=servings,
        )
        session.add(item)

    return combo


# ═══════════════════════════════════════════════════════════════════════════════
# 5. ORCHESTRATORS
# ═══════════════════════════════════════════════════════════════════════════════

def _compute_timed_meal_target(
    nutrition_target: NutritionTarget,
    tm_setting: MealPlanSettingTimedMeal,
) -> Dict[str, float]:
    """Compute absolute macro targets for a specific timed meal."""
    return {
        "calories": round(nutrition_target.calories_kcal * (tm_setting.calories_pct / 100), 1),
        "protein_g": round(nutrition_target.protein_g * (tm_setting.protein_g_pct / 100), 1),
        "carbs_g": round(nutrition_target.carbs_g * (tm_setting.carbs_g_pct / 100), 1),
        "fat_g": round(nutrition_target.fat_g * (tm_setting.fat_g_pct / 100), 1),
    }


def generate_timed_meal(
    session: Session,
    user_id: uuid.UUID,
    tm_setting: MealPlanSettingTimedMeal,
    nutrition_target: NutritionTarget,
    timed_meal: TimedMeal,
) -> Dict[str, Any]:
    """
    Generate 5 combo options for a single timed meal.
    Returns dict with timed_meal info and 5 combo_options.
    """
    # Compute target macros
    target = _compute_timed_meal_target(nutrition_target, tm_setting)

    # Resolve labels
    labels = [l.value if hasattr(l, "value") else str(l) for l in tm_setting.meal_labels]

    # Build pool
    pool = build_meal_pool(session, user_id, labels)
    if not pool:
        return {"error": "No meals available matching your criteria"}

    # Generate candidates
    candidates = generate_candidate_combos(pool, target, labels)
    if not candidates:
        return {"error": "Could not generate valid meal combos. Try adjusting targets."}

    # Ask Groq for best 5
    selected_indices = select_best_combos_via_groq(candidates, target)

    # Clear any existing combo options for this timed meal
    existing_options = session.exec(
        select(TimedMealComboOption).where(TimedMealComboOption.timed_meal_id == timed_meal.id)
    ).all()
    for opt in existing_options:
        session.delete(opt)
    session.flush()

    # Persist combos and options
    combo_options_out = []
    chosen_combo_id = None

    for rank_idx, cand_idx in enumerate(selected_indices):
        cand = candidates[cand_idx]
        combo_name = " + ".join(m.name for m, _ in cand["meals"])
        combo = _persist_combo(
            session,
            cand["meals"],
            cand["macros"],
            MealTimeType(tm_setting.meal_time.value if hasattr(tm_setting.meal_time, "value") else tm_setting.meal_time),
            combo_name,
        )

        is_chosen = rank_idx == 0
        option = TimedMealComboOption(
            timed_meal_id=timed_meal.id,
            meal_combo_id=combo.id,
            is_chosen=is_chosen,
            rank=rank_idx + 1,
        )
        session.add(option)

        if is_chosen:
            chosen_combo_id = combo.id

        combo_options_out.append({
            "rank": rank_idx + 1,
            "is_chosen": is_chosen,
            "combo_id": str(combo.id),
            "combo_name": combo_name,
            "macros": cand["macros"],
            "meals": [{"name": m.name, "servings": s, "meal_id": str(m.id)} for m, s in cand["meals"]],
        })

    # Update timed meal to point to chosen combo
    if chosen_combo_id:
        timed_meal.meal_combo_id = chosen_combo_id
        timed_meal.calories = candidates[selected_indices[0]]["macros"]["calories"]
        timed_meal.protein_g = candidates[selected_indices[0]]["macros"]["protein_g"]
        timed_meal.carbs_g = candidates[selected_indices[0]]["macros"]["carbs_g"]
        timed_meal.fat_g = candidates[selected_indices[0]]["macros"]["fat_g"]
        session.add(timed_meal)

    session.flush()

    return {
        "timed_meal_id": str(timed_meal.id),
        "meal_time": tm_setting.meal_time.value if hasattr(tm_setting.meal_time, "value") else str(tm_setting.meal_time),
        "target_macros": target,
        "combo_options": combo_options_out,
    }


def generate_day_plan(
    session: Session,
    user_id: uuid.UUID,
    plan_date: date,
    week_plan_id: Optional[uuid.UUID] = None,
) -> Dict[str, Any]:
    """Generate a full day plan with all timed meals."""
    # Get active meal plan setting
    setting = session.exec(
        select(MealPlanSetting).where(
            MealPlanSetting.created_for == user_id,
            MealPlanSetting.active == True,
        )
    ).first()
    if not setting:
        raise ValueError("No active meal plan setting found. Please create one first.")

    # Get active nutrition target
    nt = session.exec(
        select(NutritionTarget).where(
            NutritionTarget.created_for == user_id,
            NutritionTarget.active == True,
        )
    ).first()
    if not nt:
        raise ValueError("No active nutrition target found. Please set one first.")

    # Create or find existing day plan
    if week_plan_id:
        existing_day = session.exec(
            select(DayMealPlan).where(
                DayMealPlan.week_plan_id == week_plan_id,
                DayMealPlan.plan_date == plan_date,
            )
        ).first()
    else:
        existing_day = None

    if existing_day:
        day_plan = existing_day
    else:
        # If no week plan provided, create a temporary one
        if not week_plan_id:
            wp = WeekMealPlan(
                title=f"Plan for {plan_date}",
                start_date=plan_date,
                end_date=plan_date,
                user_id=user_id,
                status="active",
            )
            session.add(wp)
            session.flush()
            week_plan_id = wp.id

        day_plan = DayMealPlan(
            week_plan_id=week_plan_id,
            plan_date=plan_date,
        )
        session.add(day_plan)
        session.flush()

    # Generate timed meals
    timed_meal_results = []
    for tm_setting in setting.timed_meals:
        # Create TimedMeal record
        timed_meal = TimedMeal(
            day_plan_id=day_plan.id,
            meal_time=tm_setting.meal_time,
        )
        session.add(timed_meal)
        session.flush()

        # Generate combos
        result = generate_timed_meal(session, user_id, tm_setting, nt, timed_meal)
        timed_meal_results.append(result)

    session.commit()

    return {
        "day_plan_id": str(day_plan.id),
        "plan_date": str(plan_date),
        "timed_meals": timed_meal_results,
    }


def generate_week_plan(
    session: Session,
    user_id: uuid.UUID,
    start_date: date,
) -> Dict[str, Any]:
    """Generate a full 7-day week plan."""
    end_date = start_date + timedelta(days=6)

    week_plan = WeekMealPlan(
        title=f"Week Plan {start_date} - {end_date}",
        start_date=start_date,
        end_date=end_date,
        user_id=user_id,
        status="active",
    )
    session.add(week_plan)
    session.flush()

    day_results = []
    for day_offset in range(7):
        current_date = start_date + timedelta(days=day_offset)
        result = generate_day_plan(session, user_id, current_date, week_plan.id)
        day_results.append(result)

    session.commit()

    return {
        "week_plan_id": str(week_plan.id),
        "start_date": str(start_date),
        "end_date": str(end_date),
        "days": day_results,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 6. SWAP & REGENERATE
# ═══════════════════════════════════════════════════════════════════════════════

def swap_chosen_combo(
    session: Session,
    user_id: uuid.UUID,
    timed_meal_id: uuid.UUID,
    combo_option_id: uuid.UUID,
) -> Dict[str, Any]:
    """Swap the chosen combo for a timed meal."""
    timed_meal = session.get(TimedMeal, timed_meal_id)
    if not timed_meal:
        raise ValueError("Timed meal not found")

    # Verify ownership via day_plan -> week_plan
    day_plan = session.get(DayMealPlan, timed_meal.day_plan_id)
    if not day_plan:
        raise ValueError("Day plan not found")
    week_plan = session.get(WeekMealPlan, day_plan.week_plan_id)
    if not week_plan or week_plan.user_id != user_id:
        raise ValueError("Not authorized")

    # Get the target option
    new_option = session.get(TimedMealComboOption, combo_option_id)
    if not new_option or new_option.timed_meal_id != timed_meal_id:
        raise ValueError("Combo option not found for this timed meal")

    # Unset current chosen
    current_options = session.exec(
        select(TimedMealComboOption).where(
            TimedMealComboOption.timed_meal_id == timed_meal_id,
            TimedMealComboOption.is_chosen == True,
        )
    ).all()
    for opt in current_options:
        opt.is_chosen = False
        session.add(opt)

    # Set new chosen
    new_option.is_chosen = True
    session.add(new_option)

    # Update timed meal reference
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


def regenerate_timed_meal(
    session: Session,
    user_id: uuid.UUID,
    timed_meal_id: uuid.UUID,
) -> Dict[str, Any]:
    """Delete old options and regenerate for a timed meal."""
    timed_meal = session.get(TimedMeal, timed_meal_id)
    if not timed_meal:
        raise ValueError("Timed meal not found")

    # Verify ownership
    day_plan = session.get(DayMealPlan, timed_meal.day_plan_id)
    if not day_plan:
        raise ValueError("Day plan not found")
    week_plan = session.get(WeekMealPlan, day_plan.week_plan_id)
    if not week_plan or week_plan.user_id != user_id:
        raise ValueError("Not authorized")

    # Get active setting and nutrition target
    setting = session.exec(
        select(MealPlanSetting).where(
            MealPlanSetting.created_for == user_id,
            MealPlanSetting.active == True,
        )
    ).first()
    if not setting:
        raise ValueError("No active meal plan setting")

    nt = session.exec(
        select(NutritionTarget).where(
            NutritionTarget.created_for == user_id,
            NutritionTarget.active == True,
        )
    ).first()
    if not nt:
        raise ValueError("No active nutrition target")

    # Find corresponding timed meal setting
    meal_time_val = timed_meal.meal_time.value if hasattr(timed_meal.meal_time, "value") else str(timed_meal.meal_time)
    tm_setting = None
    for tms in setting.timed_meals:
        tms_val = tms.meal_time.value if hasattr(tms.meal_time, "value") else str(tms.meal_time)
        if tms_val == meal_time_val:
            tm_setting = tms
            break

    if not tm_setting:
        raise ValueError(f"No setting found for meal_time {meal_time_val}")

    return generate_timed_meal(session, user_id, tm_setting, nt, timed_meal)


def get_user_plans(session: Session, user_id: uuid.UUID) -> List[Dict[str, Any]]:
    """Get all week plans for a user with nested day plans and timed meals."""
    week_plans = session.exec(
        select(WeekMealPlan)
        .where(WeekMealPlan.user_id == user_id)
        .order_by(WeekMealPlan.start_date.desc())
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
                        "option_id": str(opt.id),
                        "combo_id": str(opt.meal_combo_id),
                        "combo_name": combo.name if combo else "",
                        "rank": opt.rank,
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
                    "macros": {
                        "calories": tm.calories,
                        "protein_g": tm.protein_g,
                        "carbs_g": tm.carbs_g,
                        "fat_g": tm.fat_g,
                    },
                    "combo_options": option_data,
                })

            days.append({
                "day_plan_id": str(dp.id),
                "plan_date": str(dp.plan_date),
                "timed_meals": tms,
            })

        results.append({
            "week_plan_id": str(wp.id),
            "title": wp.title,
            "start_date": str(wp.start_date),
            "end_date": str(wp.end_date),
            "status": wp.status.value if hasattr(wp.status, "value") else str(wp.status),
            "days": sorted(days, key=lambda d: d["plan_date"]),
        })

    return results
