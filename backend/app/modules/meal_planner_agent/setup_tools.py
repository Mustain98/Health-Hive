"""Setup-chatbot tools: JSON schemas (for bind_tools) + DB-backed implementations.

`build_tool_registry` returns a {name: callable} map whose functions close over the
request's DB session + user, so the generic tool loop in llm.py stays DB-agnostic.
Tools are called by the LLM ONLY when it needs the data — general chit-chat pulls no PII.
"""
from typing import Callable, Optional
import uuid

from fastapi import HTTPException
from sqlmodel import Session, select, delete

from app.modules.user.models import (
    UserData, UserHealthProfile, UserGoal, NutritionTarget,
)
from app.modules.meal.models import MealPlanSetting, MealPlanSettingTimedMeal
from app.modules.meal_planner_agent.plan_setup_models import PlanSetupSession, PlanSetupMessage
from app.modules.user import daily_goal_service as dg_service
from app.modules.user import risk
from app.modules.user.schemas import (
    DailyGoalCreate, DailyGoalUpdate, GoalType, MilestoneType,
    goal_type_for_milestone, validate_milestone_attributes,
)
from app.utils.calculate import calculate_tdee, calculate_bmi
from app.utils.text import short

_NT_BOUNDS = {"calories_kcal": (800, 10000), "protein_g": (0, 400), "carbs_g": (0, 1200), "fat_g": (0, 300)}


def _clamp(name, v):
    lo, hi = _NT_BOUNDS[name]
    return max(lo, min(hi, v))


# ── Schemas advertised to the model (OpenAI function-calling format) ─────────
TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "get_health_data",
        "description": "Everything about the user for planning in one call: body metrics (age, gender, "
                       "height, weight, activity) + derived TDEE and BMI + diet preferences + health "
                       "conditions + notes. Call it whenever the chat is about the user's plan/health; "
                       "then analyze what's relevant and explain your rationale.",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "get_current_setup",
        "description": "The user's currently ACTIVE milestone/goal, nutrition target and meal setting "
                       "(if any).",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "list_plans",
        "description": "List the user's plans (yours/AI/consultant) with each plan's id, parts and "
                       "which are active/missing. Use to view or target a specific plan or part by id.",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "continue_draft_plan",
        "description": "Point this chat at an EXISTING inactive draft plan (by id from list_plans) so "
                       "further edits build into it. Use when the user wants to keep working on a "
                       "specific earlier plan.",
        "parameters": {"type": "object", "properties": {"plan_id": {"type": "string"}},
                       "required": ["plan_id"]},
    }},
    {"type": "function", "function": {
        "name": "start_new_draft_plan",
        "description": "Begin a BRAND-NEW draft plan instead of adding to the current/latest one. Use "
                       "when the user explicitly wants a separate, different plan.",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "get_past_session_summaries",
        "description": "Short summaries of the user's previous setup chats. Call when the user refers "
                       "to something discussed before.",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "get_session_transcript",
        "description": "Full transcript of a specific past setup chat. Pass a session_id from "
                       "get_past_session_summaries (or omit to use the chat the user referenced).",
        "parameters": {"type": "object", "properties": {"session_id": {"type": "string"}}},
    }},
    # ── Daily-goal ACTIONS (targeted edits; do NOT finalize the whole plan for these) ──
    {"type": "function", "function": {
        "name": "list_daily_goals",
        "description": "List the user's daily goals with their ids. Use to find the id before "
                       "updating or deleting a daily goal.",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "add_daily_goal",
        "description": "Create a new daily goal (habit). goal_type is one of "
                       "exercise/calorie_burn/intake/steps/custom. If a goal with the same "
                       "type+name already exists it is UPDATED in place, never duplicated.",
        "parameters": {"type": "object", "properties": {
            "name": {"type": "string"}, "goal_type": {"type": "string"},
            "target_value": {"type": "number"}, "unit": {"type": "string"},
            "days_of_week": {"type": "array", "items": {"type": "integer"},
                             "description": "weekdays the habit runs, Mon=0 … Sun=6; omit or empty = every day"},
            "attributes": {"type": "object"}}, "required": ["name", "goal_type"]},
    }},
    {"type": "function", "function": {
        "name": "update_daily_goal",
        "description": "Update an existing daily goal by id. Only include the fields to change. "
                       "Use this (not add_daily_goal) to reschedule via days_of_week.",
        "parameters": {"type": "object", "properties": {
            "daily_goal_id": {"type": "string"}, "name": {"type": "string"},
            "goal_type": {"type": "string"}, "target_value": {"type": "number"},
            "unit": {"type": "string"},
            "days_of_week": {"type": "array", "items": {"type": "integer"},
                             "description": "weekdays the habit runs, Mon=0 … Sun=6; empty = every day"},
            "attributes": {"type": "object"}},
            "required": ["daily_goal_id"]},
    }},
    {"type": "function", "function": {
        "name": "delete_daily_goal",
        "description": "Delete a daily goal by id.",
        "parameters": {"type": "object", "properties": {"daily_goal_id": {"type": "string"}},
                       "required": ["daily_goal_id"]},
    }},
    # ── Milestone / nutrition target / meal setting: write INACTIVE DRAFTS (user activates later) ──
    {"type": "function", "function": {
        "name": "set_milestone",
        "description": "Create or update the user's milestone DRAFT (long-term aim). milestone_type is "
                       "one of lose_weight/gain_weight/gain_muscle/maintain. Saved inactive for the user "
                       "to activate. Unsafe/aggressive targets are refused (refer to a consultant).",
        "parameters": {"type": "object", "properties": {
            "milestone_id": {"type": "string", "description": "id to edit an existing milestone; omit to build the draft plan's"},
            "milestone_type": {"type": "string"}, "name": {"type": "string"},
            "target_weight": {"type": "number"}, "target_value": {"type": "number"},
            "unit": {"type": "string"}, "duration_days": {"type": "integer"},
            "attributes": {"type": "object"}}},
    }},
    {"type": "function", "function": {
        "name": "delete_milestone",
        "description": "Delete a milestone draft (or by id).",
        "parameters": {"type": "object", "properties": {"milestone_id": {"type": "string"}}},
    }},
    {"type": "function", "function": {
        "name": "set_nutrition_target",
        "description": "Create or update the user's nutrition-target DRAFT (daily calories + macros). "
                       "Omit macros or pass from_milestone=true to derive them from the milestone + TDEE. "
                       "Saved inactive for the user to activate.",
        "parameters": {"type": "object", "properties": {
            "target_id": {"type": "string", "description": "id to edit an existing target; omit to build the draft plan's"},
            "calories_kcal": {"type": "integer"}, "protein_g": {"type": "number"},
            "carbs_g": {"type": "number"}, "fat_g": {"type": "number"},
            "from_milestone": {"type": "boolean"}}},
    }},
    {"type": "function", "function": {
        "name": "delete_nutrition_target",
        "description": "Delete a nutrition-target draft (or by id).",
        "parameters": {"type": "object", "properties": {"target_id": {"type": "string"}}},
    }},
    {"type": "function", "function": {
        "name": "set_meal_setting",
        "description": "Create or update the user's meal-setting DRAFT (how the day's meals split). "
                       "slots = list of {meal_time (breakfast/lunch/dinner/snack), name, calories_pct, "
                       "protein_g_pct, carbs_g_pct, fat_g_pct, description}. Percentages are normalized "
                       "to 100. Saved inactive for the user to activate.",
        "parameters": {"type": "object", "properties": {
            "setting_id": {"type": "string", "description": "id to edit an existing setting; omit to build the draft plan's"},
            "name": {"type": "string"},
            "slots": {"type": "array", "items": {"type": "object"}}}},
    }},
    {"type": "function", "function": {
        "name": "delete_meal_setting",
        "description": "Delete a meal-setting draft (or by id).",
        "parameters": {"type": "object", "properties": {"setting_id": {"type": "string"}}},
    }},
]


def _enum(v):
    return v.value if hasattr(v, "value") else v


def build_tool_registry(
    session: Session, user_id: uuid.UUID, reference_session_id: Optional[uuid.UUID] = None,
    setup_session_id: Optional[uuid.UUID] = None,
) -> dict[str, Callable]:

    def get_health_data(**_):
        """Everything about the user for planning: body metrics + derived TDEE/BMI +
        diet preferences + health conditions + notes. The assistant decides which
        signals to use and must explain its rationale to the user."""
        ud = session.exec(select(UserData).where(UserData.user_id == user_id)).first()
        hp = session.get(UserHealthProfile, user_id)
        out = {
            "age": ud.age if ud else None, "gender": _enum(ud.gender) if ud else None,
            "height_cm": ud.height_cm if ud else None, "weight_kg": ud.weight_kg if ud else None,
            "activity_level": _enum(ud.activity_level) if ud else None,
            "diet_preferences": (hp.diet_preferences if hp else []) or [],
            "health_conditions": (hp.health_conditions if hp else []) or [],
            "notes": hp.notes if hp else None,
        }
        if ud and ud.height_cm and ud.weight_kg:
            out["bmi"] = calculate_bmi(ud.weight_kg, ud.height_cm)  # one signal among several
        if ud and all([ud.age, ud.gender, ud.height_cm, ud.weight_kg, ud.activity_level]):
            out["tdee_kcal"] = calculate_tdee(ud.age, _enum(ud.gender), ud.height_cm,
                                              ud.weight_kg, _enum(ud.activity_level))
        if not ud:
            out["note"] = "no body metrics on file — ask the user to fill their profile"
        return out

    def get_current_setup(**_):
        goal = session.exec(select(UserGoal).where(
            UserGoal.created_for == user_id, UserGoal.active == True)).first()  # noqa: E712
        target = session.exec(select(NutritionTarget).where(
            NutritionTarget.created_for == user_id, NutritionTarget.active == True)).first()  # noqa: E712
        setting = session.exec(select(MealPlanSetting).where(
            MealPlanSetting.created_for == user_id, MealPlanSetting.active == True)).first()  # noqa: E712
        return {
            "milestone": None if not goal else {
                "milestone_type": _enum(goal.milestone_type), "name": goal.name,
                "goal_type": _enum(goal.goal_type), "target_weight": goal.target_weight,
                "target_value": goal.target_value, "unit": goal.unit, "duration_days": goal.duration_days},
            "nutrition_target": None if not target else {
                "calories_kcal": target.calories_kcal, "protein_g": target.protein_g,
                "carbs_g": target.carbs_g, "fat_g": target.fat_g},
            "meal_setting": None if not setting else {
                "name": setting.name, "timed_meals_per_day": setting.timed_meals_per_day},
        }

    def get_past_session_summaries(**_):
        rows = session.exec(
            select(PlanSetupSession)
            .where(PlanSetupSession.user_id == user_id, PlanSetupSession.summary.is_not(None))
            .order_by(PlanSetupSession.created_at.desc())
            .limit(5)
        ).all()
        return [{"session_id": str(r.id), "created_at": str(r.created_at), "summary": r.summary}
                for r in rows]

    def get_session_transcript(session_id: Optional[str] = None, **_):
        sid = session_id or (str(reference_session_id) if reference_session_id else None)
        if not sid:
            return {"error": "no session_id provided"}
        try:
            sid_uuid = uuid.UUID(sid)
        except (ValueError, TypeError):
            return {"error": "invalid session_id"}
        owner = session.get(PlanSetupSession, sid_uuid)
        if not owner or owner.user_id != user_id:
            return {"error": "session not found"}
        msgs = session.exec(
            select(PlanSetupMessage).where(PlanSetupMessage.session_id == sid_uuid)
            .order_by(PlanSetupMessage.created_at.asc())
        ).all()
        return [{"role": _enum(m.role), "content": m.content} for m in msgs]

    # ── Daily-goal action tools (reuse the service → validation + risk checks) ──
    def _dg_dict(dg):
        return {"id": str(dg.id), "name": dg.name, "goal_type": _enum(dg.goal_type),
                "target_value": dg.target_value, "unit": dg.unit, "active": dg.active,
                "days_of_week": dg.days_of_week, "attributes": dg.attributes}

    def list_daily_goals(**_):
        return [_dg_dict(g) for g in dg_service.list_daily_goals(session, user_id)]

    def add_daily_goal(name=None, goal_type=None, target_value=None, unit=None,
                       days_of_week=None, attributes=None, **_):
        try:
            # Upsert: same type + name = the same habit — update it, never stack a duplicate.
            key = dg_service.dedup_key(goal_type, name)
            existing = next((g for g in dg_service.list_daily_goals(session, user_id)
                             if dg_service.dedup_key(g.goal_type, g.name) == key), None)
            if existing:
                fields = {k: v for k, v in (("target_value", target_value), ("unit", unit),
                                            ("days_of_week", days_of_week), ("attributes", attributes))
                          if v is not None}
                dg = dg_service.update_daily_goal(session, user_id, existing.id, DailyGoalUpdate(**fields))
                return {"ok": True, "daily_goal": _dg_dict(dg),
                        "note": "existing goal updated (no duplicate created)"}
            dg = dg_service.create_daily_goal(session, user_id, DailyGoalCreate(
                goal_type=goal_type, name=name, target_value=target_value, unit=unit,
                days_of_week=days_of_week, attributes=attributes or {},
                active=False))  # inactive draft; user activates
            dg.plan_id = _draft_plan().id  # attach to the plan this chat is building
            session.add(dg); session.commit(); session.refresh(dg)
            return {"ok": True, "daily_goal": _dg_dict(dg)}
        except HTTPException as e:
            return {"error": e.detail}
        except Exception as e:  # noqa: BLE001
            return {"error": str(e)}

    def update_daily_goal(daily_goal_id=None, **kwargs):
        fields = {k: kwargs[k] for k in ("name", "goal_type", "target_value", "unit",
                                         "days_of_week", "attributes")
                  if kwargs.get(k) is not None}
        try:
            dg = dg_service.update_daily_goal(
                session, user_id, uuid.UUID(str(daily_goal_id)), DailyGoalUpdate(**fields))
            return {"ok": True, "daily_goal": _dg_dict(dg)}
        except HTTPException as e:
            return {"error": e.detail}
        except (ValueError, TypeError):
            return {"error": "invalid daily_goal_id"}

    def delete_daily_goal(daily_goal_id=None, **_):
        try:
            dg_service.delete_daily_goal(session, user_id, uuid.UUID(str(daily_goal_id)))
            return {"ok": True}
        except HTTPException as e:
            return {"error": e.detail}
        except (ValueError, TypeError):
            return {"error": "invalid daily_goal_id"}

    # ── Plan-scoped DRAFT tools: parts attach to the draft Plan this chat builds ──
    def _setup_session():
        return session.get(PlanSetupSession, setup_session_id) if setup_session_id else None

    def _draft_plan():
        from app.modules.plan import service as plan_service
        return plan_service.get_or_create_session_draft_plan(session, user_id, _setup_session())

    def _active_milestone():
        return session.exec(select(UserGoal).where(
            UserGoal.created_for == user_id, UserGoal.active == True)).first()  # noqa: E712

    def _draft_plan_id():  # the current draft plan's id WITHOUT creating one
        s = _setup_session()
        return s.draft_plan_id if s else None

    def _milestone_of(plan_id):
        return session.exec(select(UserGoal).where(UserGoal.plan_id == plan_id)).first() if plan_id else None

    def _target_of(plan_id):
        return session.exec(select(NutritionTarget).where(NutritionTarget.plan_id == plan_id)).first() if plan_id else None

    def _setting_of(plan_id):
        return session.exec(select(MealPlanSetting).where(MealPlanSetting.plan_id == plan_id)).first() if plan_id else None

    def set_milestone(milestone_id=None, milestone_type=None, name=None, target_weight=None,
                      target_value=None, unit=None, duration_days=None, attributes=None, **_):
        if milestone_id:  # edit a specific existing milestone (active or consultant-made) in place
            g = session.get(UserGoal, uuid.UUID(str(milestone_id)))
            if not g or g.created_for != user_id:
                return {"error": "milestone not found"}
        else:  # part of the draft plan
            plan = _draft_plan()
            g = _milestone_of(plan.id) or UserGoal(created_for=user_id, created_by=user_id, active=False,
                                                   goal_type=GoalType.maintain, plan_id=plan.id)
        if milestone_type is not None:
            try:
                mt = MilestoneType(milestone_type)
            except ValueError:
                return {"error": f"invalid milestone_type {milestone_type}"}
            g.milestone_type = mt
            g.goal_type = goal_type_for_milestone(mt)
        if name is not None: g.name = short(name, 120)
        if target_weight is not None: g.target_weight = target_weight
        if target_value is not None: g.target_value = target_value
        if unit is not None: g.unit = short(unit)
        if duration_days is not None: g.duration_days = duration_days
        if attributes is not None:
            try:
                g.attributes = validate_milestone_attributes(g.milestone_type, attributes)
            except ValueError as e:
                return {"error": str(e)}
        reason = risk.is_risky_milestone(session, user_id, g)
        if reason:
            return {"error": f"unsafe milestone ({reason}) — refer the user to a consultant; not saved"}
        session.add(g); session.commit(); session.refresh(g)
        return {"ok": True, "milestone": {"id": str(g.id), "milestone_type": _enum(g.milestone_type),
                "name": g.name, "target_weight": g.target_weight, "target_value": g.target_value,
                "unit": g.unit, "duration_days": g.duration_days, "active": g.active}}

    def delete_milestone(milestone_id=None, **_):
        g = session.get(UserGoal, uuid.UUID(str(milestone_id))) if milestone_id else _milestone_of(_draft_plan_id())
        if not g or g.created_for != user_id:
            return {"error": "milestone not found"}
        from app.modules.user.models import UserGoalLog
        session.exec(delete(UserGoalLog).where(UserGoalLog.goal_id == g.id))
        session.delete(g); session.commit()
        return {"ok": True}

    def set_nutrition_target(target_id=None, calories_kcal=None, protein_g=None, carbs_g=None, fat_g=None,
                             from_milestone=False, **_):
        if from_milestone or calories_kcal is None:
            ud = session.exec(select(UserData).where(UserData.user_id == user_id)).first()
            if not ud or not all([ud.age, ud.gender, ud.height_cm, ud.weight_kg, ud.activity_level]):
                return {"error": "need body metrics (age/gender/height/weight/activity) to derive a target"}
            tdee = calculate_tdee(ud.age, _enum(ud.gender), ud.height_cm, ud.weight_kg, _enum(ud.activity_level))
            goal = _milestone_of(_draft_plan_id()) or _active_milestone()
            gt = _enum(goal.goal_type) if goal else None
            hp = session.get(UserHealthProfile, user_id)
            from app.modules.meal_planner_agent import llm as _llm
            macro = _llm.suggest_nutrition_target(tdee, gt, hp.health_conditions if hp else [],
                                                  hp.notes if hp else None)
            calories_kcal = calories_kcal if calories_kcal is not None else macro.calories_kcal
            protein_g = protein_g if protein_g is not None else macro.protein_g
            carbs_g = carbs_g if carbs_g is not None else macro.carbs_g
            fat_g = fat_g if fat_g is not None else macro.fat_g
        vals = {"calories_kcal": _clamp("calories_kcal", int(round(calories_kcal))),
                "protein_g": _clamp("protein_g", float(protein_g or 0)),
                "carbs_g": _clamp("carbs_g", float(carbs_g or 0)),
                "fat_g": _clamp("fat_g", float(fat_g or 0))}
        if target_id:  # edit a specific existing target in place
            t = session.get(NutritionTarget, uuid.UUID(str(target_id)))
            if not t or t.created_for != user_id:
                return {"error": "nutrition target not found"}
            for k, v in vals.items():
                setattr(t, k, v)
        else:
            plan = _draft_plan()
            t = _target_of(plan.id)
            if t is None:
                t = NutritionTarget(created_for=user_id, created_by=user_id, active=False, plan_id=plan.id, **vals)
            else:
                for k, v in vals.items():
                    setattr(t, k, v)
        session.add(t); session.commit(); session.refresh(t)
        return {"ok": True, "nutrition_target": {"id": str(t.id), **vals, "active": t.active}}

    def delete_nutrition_target(target_id=None, **_):
        t = session.get(NutritionTarget, uuid.UUID(str(target_id))) if target_id else _target_of(_draft_plan_id())
        if not t or t.created_for != user_id:
            return {"error": "nutrition target not found"}
        session.delete(t); session.commit()
        return {"ok": True}

    def set_meal_setting(setting_id=None, name=None, slots=None, **_):
        from app.modules.meal_planner_agent.meal_plan_service import _coerce_meal_time
        if setting_id:  # edit a specific existing setting in place
            st = session.get(MealPlanSetting, uuid.UUID(str(setting_id)))
            if not st or st.created_for != user_id:
                return {"error": "meal setting not found"}
            if name is not None:
                st.name = short(name, 120)
        else:
            plan = _draft_plan()
            st = _setting_of(plan.id)
            if st is None:
                st = MealPlanSetting(created_for=user_id, created_by=user_id, active=False, plan_id=plan.id,
                                     name=short(name or "AI Draft Plan", 120), timed_meals_per_day=0)
                session.add(st); session.flush()
            elif name is not None:
                st.name = short(name, 120)
        if slots:
            total = sum((s.get("calories_pct") or 0) for s in slots) or 100.0
            session.exec(delete(MealPlanSettingTimedMeal).where(
                MealPlanSettingTimedMeal.meal_plan_setting_id == st.id))
            for s in slots:
                pct = round((s.get("calories_pct") or 0) * 100.0 / total, 1)
                session.add(MealPlanSettingTimedMeal(
                    meal_plan_setting_id=st.id,
                    name=short(s.get("name") or s.get("meal_time") or "Meal", 100),
                    meal_time=_coerce_meal_time(s.get("meal_time")),
                    calories_pct=pct,
                    protein_g_pct=s.get("protein_g_pct", pct), carbs_g_pct=s.get("carbs_g_pct", pct),
                    fat_g_pct=s.get("fat_g_pct", pct), description=short(s.get("description"), 500)))
            st.timed_meals_per_day = len(slots)
        session.add(st); session.commit(); session.refresh(st)
        return {"ok": True, "meal_setting": {"id": str(st.id), "name": st.name,
                "timed_meals_per_day": st.timed_meals_per_day, "active": st.active}}

    def delete_meal_setting(setting_id=None, **_):
        st = session.get(MealPlanSetting, uuid.UUID(str(setting_id))) if setting_id else _setting_of(_draft_plan_id())
        if not st or st.created_for != user_id:
            return {"error": "meal setting not found"}
        session.exec(delete(MealPlanSettingTimedMeal).where(
            MealPlanSettingTimedMeal.meal_plan_setting_id == st.id))
        session.delete(st); session.commit()
        return {"ok": True}

    def list_plans_tool(**_):
        from app.modules.plan import service as plan_service
        return plan_service.list_plans(session, user_id)

    def continue_draft_plan(plan_id=None, **_):
        """Point this chat at an existing INACTIVE draft plan so further edits build into it."""
        from app.modules.plan import service as plan_service
        s = _setup_session()
        if not s:
            return {"error": "no active setup session"}
        try:
            p = plan_service.pin_session_draft_plan(session, user_id, s, uuid.UUID(str(plan_id)))
        except HTTPException as e:
            return {"error": e.detail}
        except (ValueError, TypeError):
            return {"error": "invalid plan_id"}
        return {"ok": True, "plan": plan_service.plan_dict(session, p)}

    def start_new_draft_plan_tool(**_):
        """Begin a brand-new draft plan (don't add to the current/latest one)."""
        from app.modules.plan import service as plan_service
        s = _setup_session()
        if not s:
            return {"error": "no active setup session"}
        p = plan_service.start_new_draft_plan(session, user_id, s)
        return {"ok": True, "plan": plan_service.plan_dict(session, p)}

    return {
        "get_health_data": get_health_data,
        "get_current_setup": get_current_setup,
        "list_plans": list_plans_tool,
        "continue_draft_plan": continue_draft_plan,
        "start_new_draft_plan": start_new_draft_plan_tool,
        "get_past_session_summaries": get_past_session_summaries,
        "get_session_transcript": get_session_transcript,
        "list_daily_goals": list_daily_goals,
        "add_daily_goal": add_daily_goal,
        "update_daily_goal": update_daily_goal,
        "delete_daily_goal": delete_daily_goal,
        "set_milestone": set_milestone,
        "delete_milestone": delete_milestone,
        "set_nutrition_target": set_nutrition_target,
        "delete_nutrition_target": delete_nutrition_target,
        "set_meal_setting": set_meal_setting,
        "delete_meal_setting": delete_meal_setting,
    }
