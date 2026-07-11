"""LangChain (ChatGroq) reasoning layer for meal planning.

The LLM does the *thinking* only:
  - per-timed-meal constraint generation (macros + composition rules + labels + query)
  - setup suggestions (nutrition target, meal structure) via tool-callable chains
Combo assembly/selection is deterministic (see meal_plan_service).
Every call has a deterministic fallback so generation never hard-fails.
"""
from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from typing import List, Optional

from pydantic import BaseModel, Field
from langchain_core.messages import AIMessage, ToolMessage

from app.modules.meal_planner_agent import setup_prompts as prompts

GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_FALLBACK_MODEL = "openai/gpt-oss-120b"


# ── Structured output schemas ──────────────────────────────────────────────

class MacroTarget(BaseModel):
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float


class Composition(BaseModel):
    components: List[str] = Field(description='e.g. ["main"] or ["main","side"]')
    allow_dessert: bool = False
    max_items: int = 2
    min_servings: float = 1.0
    max_servings: float = 3.0


class TimedMealConstraint(BaseModel):
    meal_time: str = Field(description="one of: breakfast, lunch, dinner, snack")
    name: str
    macros: MacroTarget
    composition: Composition
    required_labels: List[str] = []
    preferred_labels: List[str] = []
    # Condition-driven numeric nutrient limits (nullable). Set from health conditions.
    max_sodium_mg: Optional[float] = None
    min_fiber_g: Optional[float] = None
    max_sugar_g: Optional[float] = None
    retrieval_query: str = Field(description=(
        "A rich 1-2 sentence description of the ideal meal for this slot, used for semantic "
        "search. Name concrete dishes/cuisines, key proteins and ingredients, cooking method "
        "and texture, and the health framing (e.g. 'low-sodium, high-fiber, heart-healthy'). "
        "Be specific and descriptive so it retrieves relevant meals."
    ))
    rationale: str = ""


class DayConstraintPlan(BaseModel):
    slots: List[TimedMealConstraint]


class SuggestedNutritionTarget(BaseModel):
    calories_kcal: int
    protein_g: float
    carbs_g: float
    fat_g: float
    rationale: str = ""


class SuggestedSlot(BaseModel):
    meal_time: str
    name: str
    calories_pct: float


class SuggestedMealStructure(BaseModel):
    timed_meals_per_day: int
    slots: List[SuggestedSlot]


# ── LLM singleton ──────────────────────────────────────────────────────────

def _groq_api_keys() -> tuple:
    """All configured Groq API keys, in priority order."""
    keys = [os.getenv("GROQ_API_KEY"), os.getenv("GROQ_API_KEY_2"), os.getenv("GROQ_API_KEY_3")]
    keys = [k for k in keys if k]
    if not keys:
        raise RuntimeError("No Groq API key configured (GROQ_API_KEY / GROQ_API_KEY_2 / GROQ_API_KEY_3)")
    return tuple(keys)


@lru_cache(maxsize=4)
def _llm_candidates(temperature: float = 0.2) -> tuple:
    """One ChatGroq per (key, model) pair, tried in order:
    (key1, main), (key1, fallback), (key2, main), (key2, fallback), (key3, main), (key3, fallback).
    A rate-limited or failing candidate falls through to the next via LangChain fallbacks."""
    from langchain_groq import ChatGroq
    return tuple(
        ChatGroq(model=model, temperature=temperature, api_key=key)
        for key in _groq_api_keys()
        for model in (GROQ_MODEL, GROQ_FALLBACK_MODEL)
    )


def _chain(candidates):
    """First candidate with the rest attached as LangChain fallbacks."""
    cands = list(candidates)
    return cands[0].with_fallbacks(cands[1:]) if len(cands) > 1 else cands[0]


def _structured(schema, temperature: Optional[float] = None):
    cands = _llm_candidates(0.2 if temperature is None else temperature)
    return _chain([c.with_structured_output(schema) for c in cands])


# ── Constraint generation (core call) ──────────────────────────────────────

_CONSTRAINT_SYSTEM = """You are a clinical nutrition planning assistant.
Given a user's profile, their daily macro target, and an optional meal structure,
produce ONE constraint object per meal slot. For each slot decide:
- macros: split the daily macro target across slots (all slots must sum to the daily totals)
- composition: which components (main, optionally side), whether dessert is allowed, item/serving bounds
- required_labels / preferred_labels: choose ONLY from the ALLOWED LABELS list provided below. Put diet
  preferences (vegetarian/vegan/halal) in required_labels. Do NOT invent labels (no 'low_sodium',
  'high_fiber', etc. — those go in the numeric fields or the query).
- max_sodium_mg / min_fiber_g / max_sugar_g: set these numeric limits from health conditions
  (hypertension -> low max_sodium_mg e.g. 500; diabetes -> low max_sugar_g e.g. 10 and min_fiber_g e.g. 6).
  Leave null when not relevant.
- retrieval_query: a DETAILED, specific 1-2 sentence description of the ideal meal for this slot
  (used for semantic search against meals indexed by name, ingredients, cooking method and health
  context). Name concrete dishes/cuisines, key proteins and ingredients, the cooking method and
  texture, portion feel, and the open-ended health framing (e.g. 'low-sodium heart-healthy',
  'high-fiber diabetic-friendly') — put that intent HERE, not as labels. Reflect the user's
  preferences, allergies, conditions and this slot's macros. Avoid one-word queries; be descriptive
  so retrieval surfaces genuinely relevant meals.
Honor any user-pinned structure (slot count, meal_time, name, labels, calories %). Keep it realistic."""


def generate_constraints(
    profile: dict,
    macro_target: dict,
    slots: Optional[List[dict]] = None,
    allowed_labels: Optional[List[str]] = None,
) -> DayConstraintPlan:
    """slots: optional list of {meal_time, name, labels?, calories_pct?} from a MealPlanSetting.
    allowed_labels: the valid MealLabelName vocabulary the LLM may use for required/preferred_labels."""
    allowed = set(allowed_labels or [])
    user_msg = (
        f"User profile:\n{json.dumps(profile, default=str, indent=2)}\n\n"
        f"Daily macro target:\n{json.dumps(macro_target)}\n\n"
        f"ALLOWED LABELS (use only these for required_labels/preferred_labels):\n"
        f"{json.dumps(sorted(allowed))}\n\n"
        f"Meal structure (pinned by user; null = you decide):\n{json.dumps(slots, default=str)}\n\n"
        "Return one constraint per slot."
    )
    try:
        plan: DayConstraintPlan = _structured(DayConstraintPlan).invoke(
            [("system", _CONSTRAINT_SYSTEM), ("human", user_msg)]
        )
        if plan and plan.slots:
            if allowed:
                for s in plan.slots:  # strip any hallucinated labels
                    s.required_labels = [l for l in s.required_labels if l in allowed]
                    s.preferred_labels = [l for l in s.preferred_labels if l in allowed]
            return plan
    except Exception as e:  # noqa: BLE001
        print(f"[MealPlan] constraint LLM failed, using fallback: {e}")
    return _fallback_constraints(macro_target, slots, profile)


def _fallback_query(slot: dict, profile: Optional[dict]) -> str:
    """A descriptive-enough retrieval query when the LLM is unavailable."""
    meal_time = slot.get("meal_time") or "meal"
    name = slot.get("name") or meal_time.title()
    parts = [f"balanced home-style {meal_time} — {name}, moderate portion, whole foods"]
    if profile:
        diet = [str(d) for d in (profile.get("diet_preferences") or [])]
        conds = [str(c) for c in (profile.get("health_conditions") or [])]
        if diet:
            parts.append(", ".join(diet))
        if "hypertension" in conds:
            parts.append("low-sodium heart-healthy")
        if "diabetes" in conds:
            parts.append("high-fiber low-sugar diabetic-friendly")
    return ", ".join(parts)


def _fallback_constraints(macro_target: dict, slots: Optional[List[dict]],
                          profile: Optional[dict] = None) -> DayConstraintPlan:
    if slots:
        base = slots
    else:
        base = [
            {"meal_time": "breakfast", "name": "Breakfast", "calories_pct": 25},
            {"meal_time": "lunch", "name": "Lunch", "calories_pct": 35},
            {"meal_time": "dinner", "name": "Dinner", "calories_pct": 30},
            {"meal_time": "snack", "name": "Snack", "calories_pct": 10},
        ]
    n = len(base)
    out: List[TimedMealConstraint] = []
    for s in base:
        pct = s.get("calories_pct") or (100.0 / n)
        frac = pct / 100.0
        labels = s.get("labels") or ([s.get("meal_time")] if s.get("meal_time") else [])
        out.append(TimedMealConstraint(
            meal_time=s.get("meal_time", "lunch"),
            name=s.get("name", s.get("meal_time", "Meal").title()),
            macros=MacroTarget(
                calories=round(macro_target["calories"] * frac, 1),
                protein_g=round(macro_target["protein_g"] * frac, 1),
                carbs_g=round(macro_target["carbs_g"] * frac, 1),
                fat_g=round(macro_target["fat_g"] * frac, 1),
            ),
            composition=Composition(components=["main"], allow_dessert=False, max_items=2),
            required_labels=[l for l in labels if l],
            preferred_labels=[],
            retrieval_query=_fallback_query(s, profile),
            rationale="deterministic fallback",
        ))
    return DayConstraintPlan(slots=out)


# ── Setup suggestions ──────────────────────────────────────────────────────

def suggest_nutrition_target(tdee: int, goal_type: Optional[str], conditions: list, notes: Optional[str]) -> SuggestedNutritionTarget:
    user_msg = json.dumps({
        "tdee_kcal": tdee, "goal_type": goal_type,
        "health_conditions": conditions, "notes": notes,
    })
    try:
        return _structured(SuggestedNutritionTarget).invoke(
            [("system", prompts.MACRO_SYSTEM), ("human", user_msg)]
        )
    except Exception as e:  # noqa: BLE001
        print(f"[MealPlan] macro LLM failed, using fallback: {e}")
        # Deterministic fallback: goal-adjusted calories, 30/40/30 split
        cal = tdee
        if goal_type == "lose":
            cal = int(tdee * 0.82)
        elif goal_type == "gain":
            cal = int(tdee * 1.12)
        return SuggestedNutritionTarget(
            calories_kcal=cal,
            protein_g=round(cal * 0.30 / 4, 1),
            carbs_g=round(cal * 0.40 / 4, 1),
            fat_g=round(cal * 0.30 / 9, 1),
            rationale="deterministic fallback",
        )


def suggest_meal_structure(profile: dict) -> SuggestedMealStructure:
    try:
        return _structured(SuggestedMealStructure).invoke(
            [("system", prompts.STRUCTURE_SYSTEM), ("human", json.dumps(profile, default=str))]
        )
    except Exception as e:  # noqa: BLE001
        print(f"[MealPlan] structure LLM failed, using fallback: {e}")
        return SuggestedMealStructure(
            timed_meals_per_day=4,
            slots=[
                SuggestedSlot(meal_time="breakfast", name="Breakfast", calories_pct=25),
                SuggestedSlot(meal_time="lunch", name="Lunch", calories_pct=35),
                SuggestedSlot(meal_time="dinner", name="Dinner", calories_pct=30),
                SuggestedSlot(meal_time="snack", name="Snack", calories_pct=10),
            ],
        )


# ── Generic tool loop + streaming (DB- and prompt-agnostic) ─────────────────

# Groq/Llama sometimes emits tool calls as literal text in `content` instead of
# structured tool_calls; with and without the closing tag have both been observed.
_INLINE_CALL_RE = re.compile(r"<function=(\w+)>\s*(\{.*?\})\s*</function>", re.DOTALL)
_INLINE_CALL_LOOSE_RE = re.compile(r"<function=(\w+)>\s*(\{[^<]*\})?", re.DOTALL)


def parse_inline_tool_calls(text: str) -> list[dict]:
    """Extract text-format tool calls (`<function=name>{json}</function>`) from content."""
    matches = _INLINE_CALL_RE.findall(text or "") or _INLINE_CALL_LOOSE_RE.findall(text or "")
    calls = []
    for i, (name, raw) in enumerate(matches):
        try:
            args = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            args = {}
        calls.append({"name": name, "args": args, "id": f"inline_{i}"})
    return calls


def strip_inline_tool_calls(text: str) -> str:
    """Remove any tool-call syntax so it never reaches the user."""
    cleaned = _INLINE_CALL_RE.sub("", text or "")
    cleaned = _INLINE_CALL_LOOSE_RE.sub("", cleaned)
    return cleaned.replace("</function>", "").strip()


def resolve_tool_calls(messages: list, tool_schemas: list, execute_tool, max_iters: int = 4) -> list:
    """Run the model with tools bound; while it asks for tool calls, run them via the
    `execute_tool(name, args) -> result` callback and feed the results back. Returns the
    message list ending with the model's final AIMessage answer (no re-generation needed).
    Knows nothing about the DB or prompt contents."""
    bound = _chain([c.bind_tools(tool_schemas) for c in _llm_candidates()])
    msgs = list(messages)
    for _ in range(max_iters):
        ai: AIMessage = bound.invoke(msgs)
        calls = getattr(ai, "tool_calls", None)
        if not calls:
            inline = parse_inline_tool_calls(getattr(ai, "content", "") or "")
            if inline:
                ai = AIMessage(content="", tool_calls=inline)
                calls = inline
            else:
                msgs.append(ai)  # final answer — kept so the caller can stream it as-is
                return msgs
        msgs.append(ai)
        for tc in calls:
            try:
                result = execute_tool(tc["name"], tc.get("args") or {})
            except Exception as e:  # noqa: BLE001
                result = {"error": str(e)}
            msgs.append(ToolMessage(content=json.dumps(result, default=str), tool_call_id=tc["id"]))
    return msgs


def stream_text(messages: list):
    """Stream a plain (no-tools) completion as text deltas."""
    llm = _chain(_llm_candidates())
    for chunk in llm.stream(messages):
        piece = getattr(chunk, "content", "") or ""
        if piece:
            yield piece


def summarize_session(history: List[dict]) -> str:
    """Short rolling-memory summary of a finished setup chat."""
    convo = "\n".join(f"{m.get('role')}: {m.get('content','')}" for m in history)
    try:
        resp = _chain(_llm_candidates()).invoke(
            [("system", prompts.SUMMARIZE_SYSTEM), ("human", convo)]
        )
        return (getattr(resp, "content", None) or "").strip()
    except Exception as e:  # noqa: BLE001
        print(f"[Setup] summarize failed: {e}")
        return ""


# Strict, bounded finalize schema. LLM output is untrusted: these bounds mean
# out-of-range values are rejected at parse time (decision 11).

class SetupMilestone(BaseModel):
    milestone_type: str = Field(description="one of: lose_weight, gain_weight, gain_muscle, maintain")
    name: str
    target_weight: Optional[float] = Field(default=None, ge=20, le=400)
    target_value: Optional[float] = Field(default=None, description="generic target, e.g. kg of muscle")
    unit: Optional[str] = None
    duration_days: Optional[int] = Field(default=None, ge=1, le=1825)
    attributes: dict = {}


class SetupDailyGoal(BaseModel):
    goal_type: str = Field(description="one of: exercise, calorie_burn, intake, steps, custom")
    name: str
    target_value: Optional[float] = None
    unit: Optional[str] = None
    attributes: dict = {}


class SetupNutritionTarget(BaseModel):
    calories_kcal: int = Field(ge=800, le=10000)
    protein_g: float = Field(ge=0, le=400)
    carbs_g: float = Field(ge=0, le=1200)
    fat_g: float = Field(ge=0, le=300)
    rationale: str = ""


class SetupSlot(BaseModel):
    meal_time: str = Field(description="MUST be exactly one of: breakfast, lunch, dinner, snack. "
                           "Use 'snack' for any extra eating occasion (mid-morning, brunch, pre-workout, etc.)")
    name: str
    calories_pct: float = Field(ge=0, le=100)
    protein_g_pct: float = Field(ge=0, le=100)
    carbs_g_pct: float = Field(ge=0, le=100)
    fat_g_pct: float = Field(ge=0, le=100)
    description: Optional[str] = Field(default=None, description="free-text guidance (foods, cuisines, health intent)")


class SetupMealSetting(BaseModel):
    name: str
    timed_meals_per_day: int = Field(ge=1, le=12)
    slots: List[SetupSlot]


class SetupFinalize(BaseModel):
    milestone: SetupMilestone
    daily_goals: List[SetupDailyGoal] = []
    nutrition_target: SetupNutritionTarget
    meal_setting: SetupMealSetting
    summary: str = ""


def setup_finalize(profile: dict, history: List[dict], tdee: Optional[int] = None) -> SetupFinalize:
    """Turn the conversation into structured, bounded drafts. Raises on invalid output."""
    convo = "\n".join(f"{m.get('role')}: {m.get('content','')}" for m in history)
    user_msg = (
        f"User data:\n{json.dumps(profile, default=str, indent=2)}\n\n"
        f"Estimated TDEE (kcal/day): {tdee}\n\n"
        f"Conversation so far:\n{convo}\n\n"
        "Return the finalized drafts."
    )
    return _structured(SetupFinalize).invoke(
        [("system", prompts.FINALIZE_SYSTEM), ("human", user_msg)]
    )
