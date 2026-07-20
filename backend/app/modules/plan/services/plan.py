"""Plan service — a Plan groups a milestone + daily goals + nutrition target +
meal setting and is activated as a UNIT (one active plan per user; its parts go
live together). The meal pipeline still reads the active NutritionTarget +
MealPlanSetting, which are now exactly the active plan's parts.
"""
import uuid
from typing import Optional

from fastapi import HTTPException
from sqlmodel import Session, select, delete

from app.modules.plan.models import Plan, PlanSource
from app.modules.milestone.models import Milestone, MilestoneLog
from app.modules.nutrition_target.models import NutritionTarget
from app.modules.nutrition_target.schemas import NutritionTargetUpdate
from app.modules.daily_goal.models import DailyGoal, DailyGoalLog
from app.modules.meal_plan_setting.models import MealPlanSetting, MealPlanSettingTimedMeal
from app.modules.milestone import services as user_goal_service
from app.modules.nutrition_target import services as nutrition_target_service
from app.modules.daily_goal import services as daily_goal_service
from app.modules.milestone.services import risk as milestone_risk
from app.modules.daily_goal.services import risk as daily_goal_risk
from app.modules.daily_goal.schemas import DailyGoalCreate, DailyGoalType, validate_daily_goal_attributes
from app.modules.milestone.schemas import MilestoneType, goal_type_for_milestone, validate_milestone_attributes
from app.modules.notification.services import notification as notif_service
from app.modules.notification.models import NotificationType
from app.utils.time import utc_now


def _enum(v):
    return v.value if hasattr(v, "value") else v


# ── Assemble a plan + its parts ─────────────────────────────────────────────

def _parts(session: Session, plan_id: uuid.UUID):
    milestone = session.exec(select(Milestone).where(Milestone.plan_id == plan_id)).first()
    target = session.exec(select(NutritionTarget).where(NutritionTarget.plan_id == plan_id)).first()
    setting = session.exec(select(MealPlanSetting).where(MealPlanSetting.plan_id == plan_id)).first()
    dailies = list(session.exec(select(DailyGoal).where(DailyGoal.plan_id == plan_id)).all())
    return milestone, target, setting, dailies


def _milestone_dict(m: Optional[Milestone]):
    if not m:
        return None
    return {"id": str(m.id), "milestone_type": _enum(m.milestone_type), "name": m.name,
            "target_weight": m.target_weight, "target_value": m.target_value, "unit": m.unit,
            "duration_days": m.duration_days, "active": m.active, "attributes": m.attributes}


def _target_dict(t: Optional[NutritionTarget]):
    if not t:
        return None
    return {"id": str(t.id), "calories_kcal": t.calories_kcal, "protein_g": t.protein_g,
            "carbs_g": t.carbs_g, "fat_g": t.fat_g, "active": t.active}


def _setting_dict(session: Session, s: Optional[MealPlanSetting]):
    if not s:
        return None
    tms = session.exec(select(MealPlanSettingTimedMeal).where(
        MealPlanSettingTimedMeal.meal_plan_setting_id == s.id)).all()
    return {"id": str(s.id), "name": s.name, "timed_meals_per_day": s.timed_meals_per_day, "active": s.active,
            "timed_meals": [{"name": tm.name, "meal_time": _enum(tm.meal_time), "calories_pct": tm.calories_pct,
                             "protein_g_pct": tm.protein_g_pct, "carbs_g_pct": tm.carbs_g_pct,
                             "fat_g_pct": tm.fat_g_pct, "description": tm.description,
                             "meal_labels": [_enum(l) for l in tm.meal_labels]} for tm in tms]}


def _dg_dict(d: DailyGoal):
    return {"id": str(d.id), "name": d.name, "goal_type": _enum(d.goal_type),
            "target_value": d.target_value, "unit": d.unit, "active": d.active, 
            "days_of_week": d.days_of_week, "attributes": d.attributes}


def plan_dict(session: Session, plan: Plan) -> dict:
    m, t, st, dgs = _parts(session, plan.id)
    missing = [k for k, v in (("milestone", m), ("nutrition_target", t), ("meal_setting", st)) if not v]
    return {
        "id": str(plan.id), "name": plan.name, "source": _enum(plan.source), "active": plan.active,
        # ISO-8601, not str(datetime) — the latter is not parseable by Date() in every browser.
        "created_at": plan.created_at.isoformat() if plan.created_at else None,
        "milestone": _milestone_dict(m), "nutrition_target": _target_dict(t),
        "meal_setting": _setting_dict(session, st), "daily_goals": [_dg_dict(d) for d in dgs],
        "missing": missing,
    }


# ── CRUD ────────────────────────────────────────────────────────────────────

def _owned(session: Session, user_id: uuid.UUID, plan_id: uuid.UUID) -> Plan:
    p = session.get(Plan, plan_id)
    if not p or p.created_for != user_id:
        raise HTTPException(status_code=404, detail="Plan not found")
    return p


# ── Setup-chat draft plan (durable across sessions) ─────────────────────────

def get_or_create_session_draft_plan(session: Session, user_id: uuid.UUID, setup_session,
                                     *, name: str = "AI plan") -> Plan:
    """The draft plan this setup session is editing. Reuses setup_session.draft_plan_id when it
    points to an inactive, user-owned plan; else adopts the user's latest inactive AI draft ONLY
    if it is still empty; else creates one. Records the pointer on the session. flush() so the id
    is available; caller commits.

    The emptiness condition matters. Adopting any latest draft meant a brand-new chat inherited
    the previous chat's plan — and since a plan holds exactly one milestone, "create me a
    milestone" silently overwrote the earlier one instead of starting fresh. An empty draft is
    just an unused shell (typically created by a chat that never wrote anything), so reusing
    that one avoids littering the Plans page without ever clobbering real work.
    """
    if setup_session and setup_session.draft_plan_id:
        p = session.get(Plan, setup_session.draft_plan_id)
        if p and p.created_for == user_id and not p.active:
            return p
    latest = session.exec(select(Plan).where(
        Plan.created_for == user_id, Plan.active == False, Plan.source == PlanSource.ai)  # noqa: E712
        .order_by(Plan.created_at.desc())).first()
    if latest and any(_parts(session, latest.id)):
        latest = None  # has real content — leave it alone and start a new draft
    p = latest or Plan(created_for=user_id, created_by=user_id, source=PlanSource.ai, name=name, active=False)
    if not latest:
        session.add(p)
        session.flush()
    if setup_session:
        setup_session.draft_plan_id = p.id
        session.add(setup_session)
    return p


def pin_session_draft_plan(session: Session, user_id: uuid.UUID, setup_session,
                           plan_id: uuid.UUID) -> Plan:
    """Point the session at a specific existing inactive draft (Continue editing / continue_draft_plan)."""
    p = _owned(session, user_id, plan_id)
    if p.active:
        raise HTTPException(status_code=409,
                            detail="That plan is already active — deactivate it to edit as a draft.")
    setup_session.draft_plan_id = p.id
    session.add(setup_session)
    session.commit()
    return p


def start_new_draft_plan(session: Session, user_id: uuid.UUID, setup_session,
                         *, name: str = "AI plan") -> Plan:
    """Create a fresh draft and pin the session to it ('+ New plan')."""
    p = Plan(created_for=user_id, created_by=user_id, source=PlanSource.ai, name=name, active=False)
    session.add(p)
    session.flush()
    setup_session.draft_plan_id = p.id
    session.add(setup_session)
    session.commit()
    return p


def list_plans(session: Session, user_id: uuid.UUID) -> list[dict]:
    plans = session.exec(select(Plan).where(Plan.created_for == user_id)
                         .order_by(Plan.active.desc(), Plan.created_at.desc())).all()
    return [plan_dict(session, p) for p in plans]


def get_plan(session: Session, user_id: uuid.UUID, plan_id: uuid.UUID) -> dict:
    return plan_dict(session, _owned(session, user_id, plan_id))


def create_plan(session: Session, user_id: uuid.UUID, name: Optional[str], source: Optional[str]) -> Plan:
    try:
        src = PlanSource(source) if source else PlanSource.self_
    except ValueError:
        src = PlanSource.self_
    p = Plan(created_for=user_id, created_by=user_id, name=(name or "My Plan")[:255], source=src)
    session.add(p)
    session.commit()
    session.refresh(p)
    return p


def create_plan_for_client(session: Session, consultant_id: uuid.UUID, client_id: uuid.UUID,
                           payload: dict) -> dict:
    """Consultant builds a whole INACTIVE plan for a client (source=consultant).
    payload: {name, milestone?, daily_goals?[], nutrition_target?, meal_setting?} — partial allowed.
    Parts stay inactive; risk guards run when the client activates the plan."""
    milestone = payload.get("milestone")
    daily_goals = payload.get("daily_goals") or []
    target = payload.get("nutrition_target")
    setting = payload.get("meal_setting")

    # Validate types + attributes up-front so we don't leave a half-built plan on a 422.
    ms_type = None
    try:
        if milestone:
            ms_type = MilestoneType(milestone["milestone_type"]) if milestone.get("milestone_type") else None
            validate_milestone_attributes(ms_type, milestone.get("attributes") or {})
        for dg in daily_goals:
            validate_daily_goal_attributes(DailyGoalType(dg.get("goal_type")), dg.get("attributes") or {})
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=422, detail=f"Invalid plan payload: {e}")

    plan = Plan(created_for=client_id, created_by=consultant_id, source=PlanSource.consultant,
                name=(payload.get("name") or "Consultant plan")[:255], active=False)
    session.add(plan)
    session.flush()

    if milestone:
        g = user_goal_service.create_goal_for_user(session, client_id, Milestone(
            created_for=client_id, created_by=consultant_id,
            goal_type=goal_type_for_milestone(ms_type),
            milestone_type=ms_type,
            name=milestone.get("name"), target_weight=milestone.get("target_weight"),
            target_value=milestone.get("target_value"), unit=milestone.get("unit"),
            duration_days=milestone.get("duration_days"),
            attributes=milestone.get("attributes") or {}, active=False,
        ))
        g.plan_id = plan.id
        session.add(g)

    for dg in daily_goals:
        row = daily_goal_service.create_daily_goal(session, client_id, DailyGoalCreate(
            goal_type=dg.get("goal_type"), name=dg.get("name"),
            target_value=dg.get("target_value"), unit=dg.get("unit"),
            days_of_week=dg.get("days_of_week"), attributes=dg.get("attributes") or {},
            active=False,
        ), created_by=consultant_id)
        row.plan_id = plan.id
        session.add(row)

    if target:
        t = nutrition_target_service.create_target_for_user(
            session, client_id, NutritionTargetUpdate(
                calories_kcal=target.get("calories_kcal"), protein_g=target.get("protein_g"),
                carbs_g=target.get("carbs_g"), fat_g=target.get("fat_g"), active=False,
            ), created_by=consultant_id)
        t.plan_id = plan.id
        session.add(t)

    if setting:
        # Lazy import: consultant_manage_user_service imports this module.
        from app.modules.consultant.services.manage_user import consultant_create_meal_plan_setting
        data = consultant_create_meal_plan_setting(session, consultant_id, client_id, setting)
        st = session.get(MealPlanSetting, uuid.UUID(str(data["id"])))
        if st:
            st.plan_id = plan.id
            session.add(st)

    notif_service.create(
        session, client_id, NotificationType.setup_ready,
        title="Your consultant built you a plan",
        body=f"Review and activate \"{plan.name}\" on your Plans page.",
        data={"plan_id": str(plan.id)},
    )
    session.commit()
    session.refresh(plan)
    return plan_dict(session, plan)


def rename_plan(session: Session, user_id: uuid.UUID, plan_id: uuid.UUID, name: str) -> Plan:
    p = _owned(session, user_id, plan_id)
    p.name = (name or p.name)[:255]
    p.updated_at = utc_now()
    session.add(p)
    session.commit()
    session.refresh(p)
    return p


# ── Activation as a unit ────────────────────────────────────────────────────

def _activate_setting(session: Session, user_id: uuid.UUID, setting: MealPlanSetting) -> None:
    for ex in session.exec(select(MealPlanSetting).where(
            MealPlanSetting.created_for == user_id, MealPlanSetting.active == True)).all():  # noqa: E712
        if ex.id != setting.id:
            ex.active = False
            session.add(ex)
    session.flush()
    setting.active = True
    session.add(setting)
    session.commit()


def activate_plan(session: Session, user_id: uuid.UUID, plan_id: uuid.UUID) -> dict:
    plan = _owned(session, user_id, plan_id)
    m, t, st, dgs = _parts(session, plan.id)

    # Safety: no unsafe milestone/daily-goal goes live (decision 3).
    if m:
        milestone_risk.assert_safe_milestone(session, user_id, m)
    for d in dgs:
        daily_goal_risk.assert_safe_daily_goal(session, user_id, d)

    # Deactivate other plans (the flag; their parts are deactivated by the per-part activators).
    for op in session.exec(select(Plan).where(
            Plan.created_for == user_id, Plan.active == True)).all():  # noqa: E712
        if op.id != plan.id:
            op.active = False
            session.add(op)
    session.flush()

    # Activate each part via the existing single-active activators (they deactivate others of their kind).
    if m:
        user_goal_service.activate_goal_for_user(session, user_id, m.id)
    if t:
        nutrition_target_service.activate_target_for_user(session, user_id, t.id)
    if st:
        _activate_setting(session, user_id, st)

    # Daily goals: deactivate all the user's active dailies, then activate this plan's.
    for d in session.exec(select(DailyGoal).where(
            DailyGoal.created_for == user_id, DailyGoal.active == True)).all():  # noqa: E712
        d.active = False
        session.add(d)
    session.flush()
    for d in dgs:
        d.active = True
        session.add(d)

    plan.active = True
    plan.updated_at = utc_now()
    session.add(plan)
    session.commit()
    return plan_dict(session, plan)


def deactivate_plan(session: Session, user_id: uuid.UUID, plan_id: uuid.UUID) -> dict:
    plan = _owned(session, user_id, plan_id)
    m, t, st, dgs = _parts(session, plan.id)
    for part in (m, t, st, *dgs):
        if part is not None:
            part.active = False
            session.add(part)
    plan.active = False
    plan.updated_at = utc_now()
    session.add(plan)
    session.commit()
    return plan_dict(session, plan)


def delete_plan(session: Session, user_id: uuid.UUID, plan_id: uuid.UUID) -> None:
    plan = _owned(session, user_id, plan_id)
    m, t, st, dgs = _parts(session, plan.id)
    if m:
        session.exec(delete(MilestoneLog).where(MilestoneLog.goal_id == m.id))
        session.delete(m)
    if t:
        session.delete(t)
    if st:
        session.exec(delete(MealPlanSettingTimedMeal).where(
            MealPlanSettingTimedMeal.meal_plan_setting_id == st.id))
        session.delete(st)
    for d in dgs:
        session.exec(delete(DailyGoalLog).where(DailyGoalLog.daily_goal_id == d.id))
        session.delete(d)
    session.delete(plan)
    session.commit()
