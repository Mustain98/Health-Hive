"""Setup chatbot service.

Conversational turns (context = user data + prior messages, capped at MAX_MESSAGES),
plus a `finalize` that validates the LLM's structured output (bounded), runs the risk
guard, and either persists INACTIVE drafts + a notification or refers to a consultant.
Generation is separate from activation — finalize never activates anything.
"""
import json
import logging
import uuid
from typing import Iterator, Optional

from fastapi import HTTPException
from langchain_core.messages import AIMessage
from sqlmodel import Session, select

from app.core.database import engine
from app.modules.meal_planner_agent.plan_setup_models import (
    PlanSetupSession, PlanSetupMessage, SetupSessionStatus, SetupRole, MAX_MESSAGES,
)
from app.modules.meal_planner_agent import llm as llm_mod
from app.modules.meal_planner_agent import setup_prompts as prompts
from app.modules.meal_planner_agent import setup_tools
from app.modules.meal_planner_agent.meal_plan_service import assemble_profile, _coerce_meal_time
from app.utils.calculate import calculate_tdee

from app.modules.user.models import UserGoal, NutritionTarget, DailyGoal
from app.modules.meal.models import MealPlanSetting, MealPlanSettingTimedMeal
from app.modules.user.schemas import (
    MilestoneType, DailyGoalType, goal_type_for_milestone,
    validate_milestone_attributes, validate_daily_goal_attributes,
)
from app.modules.user import risk
from app.utils.text import short
from app.modules.notification import service as notif_service
from app.modules.notification.models import NotificationType

logger = logging.getLogger(__name__)


# ── Sessions & messages ─────────────────────────────────────────────────────

def start_session(session: Session, user_id: uuid.UUID) -> PlanSetupSession:
    s = PlanSetupSession(user_id=user_id)
    session.add(s)
    session.commit()
    session.refresh(s)
    # Seed a friendly opener so the UI has something to show.
    opener = PlanSetupMessage(
        session_id=s.id, role=SetupRole.assistant,
        content="Hi! Let's set up your plan. What are you aiming for — losing weight, "
                "gaining muscle, or maintaining? Feel free to include a rough timeframe.",
    )
    session.add(opener)
    s.message_count = 1
    session.add(s)
    session.commit()
    session.refresh(s)
    return s


def _owned_session(session: Session, user_id: uuid.UUID, session_id: uuid.UUID) -> PlanSetupSession:
    s = session.get(PlanSetupSession, session_id)
    if not s or s.user_id != user_id:
        raise HTTPException(status_code=404, detail="Setup session not found")
    return s


def _messages(session: Session, session_id: uuid.UUID) -> list[PlanSetupMessage]:
    return list(session.exec(
        select(PlanSetupMessage)
        .where(PlanSetupMessage.session_id == session_id)
        .order_by(PlanSetupMessage.created_at.asc())
    ).all())


def _history(msgs: list[PlanSetupMessage]) -> list[dict]:
    return [
        {"role": m.role.value if hasattr(m.role, "value") else m.role, "content": m.content}
        for m in msgs if m.role != SetupRole.system
    ]


def get_session(session: Session, user_id: uuid.UUID, session_id: uuid.UUID) -> dict:
    s = _owned_session(session, user_id, session_id)
    msgs = _messages(session, session_id)
    return {
        "id": str(s.id),
        "status": s.status.value if hasattr(s.status, "value") else s.status,
        "message_count": s.message_count,
        "limit_reached": s.message_count >= MAX_MESSAGES,
        "max_messages": MAX_MESSAGES,
        "messages": _history(msgs),
    }


def list_sessions(session: Session, user_id: uuid.UUID) -> list[dict]:
    rows = session.exec(
        select(PlanSetupSession).where(PlanSetupSession.user_id == user_id)
        .order_by(PlanSetupSession.created_at.desc())
    ).all()
    out = []
    for s in rows:
        first_user = session.exec(
            select(PlanSetupMessage).where(
                PlanSetupMessage.session_id == s.id, PlanSetupMessage.role == SetupRole.user)
            .order_by(PlanSetupMessage.created_at.asc()).limit(1)
        ).first()
        preview = (s.summary or (first_user.content if first_user else "New chat"))[:80]
        out.append({
            "id": str(s.id),
            "status": s.status.value if hasattr(s.status, "value") else s.status,
            "message_count": s.message_count,
            "created_at": str(s.created_at),
            "preview": preview,
        })
    return out


def get_latest_open_session(session: Session, user_id: uuid.UUID) -> Optional[PlanSetupSession]:
    return session.exec(
        select(PlanSetupSession).where(
            PlanSetupSession.user_id == user_id, PlanSetupSession.status == SetupSessionStatus.open)
        .order_by(PlanSetupSession.created_at.desc()).limit(1)
    ).first()


def validate_turn(session: Session, user_id: uuid.UUID, session_id: uuid.UUID, content: str) -> None:
    """Synchronous guard so the router can return clean HTTP errors before streaming."""
    s = _owned_session(session, user_id, session_id)
    if s.status == SetupSessionStatus.closed:
        raise HTTPException(status_code=409, detail="This session is closed. Please open a new session.")
    if s.message_count >= MAX_MESSAGES:
        s.status = SetupSessionStatus.closed
        session.add(s)
        session.commit()
        raise HTTPException(status_code=409, detail="Chat limit reached — please open a new session.")
    if not (content or "").strip():
        raise HTTPException(status_code=400, detail="Message is empty")


def _lc_messages(history: list[dict], reference_session_id: Optional[uuid.UUID]) -> list:
    msgs = [("system", prompts.CHAT_SYSTEM)]
    if reference_session_id:
        msgs.append(("system", f"The user is referencing an earlier chat (session id "
                               f"{reference_session_id}). Call get_session_transcript if you need its details."))
    for m in history:
        msgs.append(("ai" if m["role"] == "assistant" else "human", m["content"]))
    return msgs


def stream_turn(user_id: uuid.UUID, session_id: uuid.UUID, content: str,
                reference_session_id: Optional[uuid.UUID] = None) -> Iterator[str]:
    """SSE generator. Uses its OWN DB session (the request-scoped one is closed once the
    StreamingResponse body runs). Persists the user message, resolves tools, streams the
    reply, then persists the assistant message + updates counts/status."""
    with Session(engine) as db:
        s = db.get(PlanSetupSession, session_id)
        if not s or s.user_id != user_id:
            yield _sse({"error": "session not found"}); return

        content = content.strip()
        db.add(PlanSetupMessage(session_id=s.id, role=SetupRole.user, content=content))
        s.message_count += 1
        db.commit()

        history = _history(_messages(db, session_id))
        messages = _lc_messages(history, reference_session_id)
        registry = setup_tools.build_tool_registry(db, user_id, reference_session_id, setup_session_id=session_id)

        def execute_tool(name, args):
            fn = registry.get(name)
            return fn(**(args or {})) if fn else {"error": f"unknown tool {name}"}

        try:
            prepared = llm_mod.resolve_tool_calls(messages, setup_tools.TOOL_SCHEMAS, execute_tool)
            # The tool loop already produced the final answer — stream it as-is instead of
            # paying for a second full-context generation.
            reply = ""
            last = prepared[-1] if prepared else None
            if isinstance(last, AIMessage) and not getattr(last, "tool_calls", None):
                reply = llm_mod.strip_inline_tool_calls(str(last.content or ""))
            if not reply:  # tool loop exhausted without an answer — one plain pass
                reply = llm_mod.strip_inline_tool_calls("".join(llm_mod.stream_text(prepared)))
            reply = reply.strip() or "Sorry, could you rephrase that?"
            for i in range(0, len(reply), 60):
                yield _sse({"delta": reply[i:i + 60]})
        except Exception as e:  # noqa: BLE001
            logger.exception("[Setup] stream failed for session %s", session_id)
            msg = str(e).lower()
            if any(k in msg for k in ("context_length", "context length", "too large", "rate_limit", "rate limit")):
                reply = "This chat has gotten long — please start a new session to continue."
            else:
                reply = "I'm having trouble responding right now — please try again."
            yield _sse({"delta": reply})

        db.add(PlanSetupMessage(session_id=s.id, role=SetupRole.assistant, content=reply))
        s.message_count += 1
        if s.message_count >= MAX_MESSAGES:
            s.status = SetupSessionStatus.closed
            s.summary = llm_mod.summarize_session(_history(_messages(db, session_id)))
        db.add(s)
        db.commit()

        yield _sse({
            "done": True,
            "message_count": s.message_count,
            "limit_reached": s.message_count >= MAX_MESSAGES,
            "status": s.status.value if hasattr(s.status, "value") else s.status,
        })


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj, default=str)}\n\n"


# ── Finalize → inactive drafts / consultant referral ────────────────────────

def _tdee_for(profile: dict) -> Optional[int]:
    body = profile.get("body") or {}
    if all(body.get(k) for k in ("age", "gender", "height_cm", "weight_kg", "activity_level")):
        return calculate_tdee(body["age"], body["gender"], body["height_cm"], body["weight_kg"], body["activity_level"])
    return None


def finalize(session: Session, user_id: uuid.UUID, session_id: uuid.UUID) -> dict:
    s = _owned_session(session, user_id, session_id)
    profile = assemble_profile(session, user_id)
    tdee = _tdee_for(profile)
    history = _history(_messages(session, session_id))

    # 1) Untrusted LLM output → strict bounded parse.
    try:
        draft = llm_mod.setup_finalize(profile, history, tdee)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"Couldn't produce a valid setup: {e}. Try refining the chat.")

    # 2) Build (unsaved) milestone + daily goals for the risk guard.
    try:
        mtype = MilestoneType(draft.milestone.milestone_type)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid milestone_type: {draft.milestone.milestone_type}")

    goal = UserGoal(
        created_for=user_id, created_by=user_id, active=False,
        goal_type=goal_type_for_milestone(mtype),
        milestone_type=mtype, name=short(draft.milestone.name, 120),
        target_weight=draft.milestone.target_weight, target_value=draft.milestone.target_value,
        unit=short(draft.milestone.unit), duration_days=draft.milestone.duration_days,
        attributes=validate_milestone_attributes(mtype, draft.milestone.attributes),
    )

    daily_goals: list[DailyGoal] = []
    for dg in draft.daily_goals[:5]:  # cap: don't dump a whole exercise program
        try:
            gt = DailyGoalType(dg.goal_type)
        except ValueError:
            continue  # skip unknown daily-goal types rather than fail the whole finalize
        daily_goals.append(DailyGoal(
            created_for=user_id, created_by=user_id, active=False,
            goal_type=gt, name=short(dg.name, 120), target_value=dg.target_value, unit=short(dg.unit),
            attributes=validate_daily_goal_attributes(gt, dg.attributes),
        ))

    # 3) Risk guard — AI must not produce unsafe drafts; refer to a consultant instead.
    reasons = [r for r in (
        risk.is_risky_milestone(session, user_id, goal),
        *[risk.is_risky_daily_goal(session, user_id, d) for d in daily_goals],
    ) if r]
    if reasons:
        s.summary = draft.summary or f"Referred to consultant: {reasons[0]}"
        session.add(s)
        notif_service.create(
            session, user_id, NotificationType.consult_referral,
            title="A consultant should set this up",
            body="Your goal looks aggressive, so we didn't auto-generate it. " + reasons[0],
            data={"reasons": reasons}, commit=True,
        )
        return {"refer_to_consultant": True, "reasons": reasons, "summary": draft.summary}

    # 4) Persist INACTIVE drafts as ONE Plan (never activated here).
    from app.modules.plan.models import Plan, PlanSource
    plan = Plan(created_for=user_id, created_by=user_id, source=PlanSource.ai,
                name=short(goal.name or "AI plan", 120), active=False)
    session.add(plan); session.flush()
    goal.plan_id = plan.id
    for d in daily_goals:
        d.plan_id = plan.id
    target = NutritionTarget(
        created_for=user_id, created_by=user_id, active=False, plan_id=plan.id,
        calories_kcal=draft.nutrition_target.calories_kcal, protein_g=draft.nutrition_target.protein_g,
        carbs_g=draft.nutrition_target.carbs_g, fat_g=draft.nutrition_target.fat_g,
    )
    setting = MealPlanSetting(
        created_for=user_id, created_by=user_id, active=False, plan_id=plan.id,
        name=draft.meal_setting.name, timed_meals_per_day=draft.meal_setting.timed_meals_per_day,
    )
    session.add_all([goal, *daily_goals, target, setting])
    session.flush()  # need setting.id for its timed meals
    s.draft_plan_id = plan.id
    session.add(s)

    for slot in draft.meal_setting.slots:
        session.add(MealPlanSettingTimedMeal(
            meal_plan_setting_id=setting.id, name=slot.name,
            meal_time=_coerce_meal_time(slot.meal_time),  # normalize to the enum
            calories_pct=slot.calories_pct, protein_g_pct=slot.protein_g_pct,
            carbs_g_pct=slot.carbs_g_pct, fat_g_pct=slot.fat_g_pct, description=slot.description,
        ))

    notif_service.create(
        session, user_id, NotificationType.setup_ready,
        title="Your plan setup is ready to review",
        body="Review your milestone, nutrition target and meal setting, then activate them.",
        data={
            "milestone_id": str(goal.id), "nutrition_target_id": str(target.id),
            "meal_setting_id": str(setting.id),
            "daily_goal_ids": [str(d.id) for d in daily_goals],
        },
    )
    s.summary = draft.summary or f"Plan drafted: {goal.name or mtype.value}"
    session.add(s)
    session.commit()

    return {
        "refer_to_consultant": False,
        "summary": draft.summary,
        "plan_id": str(plan.id),
        "milestone": {"id": str(goal.id), "milestone_type": mtype.value, "name": goal.name,
                      "target_weight": goal.target_weight, "target_value": goal.target_value,
                      "unit": goal.unit, "duration_days": goal.duration_days},
        "daily_goals": [{"id": str(d.id), "goal_type": d.goal_type.value, "name": d.name,
                         "target_value": d.target_value, "unit": d.unit} for d in daily_goals],
        "nutrition_target": {"id": str(target.id), "calories_kcal": target.calories_kcal,
                             "protein_g": target.protein_g, "carbs_g": target.carbs_g, "fat_g": target.fat_g},
        "meal_setting": {"id": str(setting.id), "name": setting.name,
                         "timed_meals_per_day": setting.timed_meals_per_day,
                         "slots": [{"meal_time": s.meal_time, "name": s.name, "calories_pct": s.calories_pct,
                                    "description": s.description} for s in draft.meal_setting.slots]},
    }


def pin_draft_plan(session: Session, user_id: uuid.UUID, session_id: uuid.UUID,
                   plan_id: uuid.UUID) -> dict:
    """Point the session at an existing inactive draft plan ('Continue editing')."""
    from app.modules.plan import service as plan_service
    s = _owned_session(session, user_id, session_id)
    p = plan_service.pin_session_draft_plan(session, user_id, s, plan_id)
    return plan_service.plan_dict(session, p)


def new_draft_plan(session: Session, user_id: uuid.UUID, session_id: uuid.UUID) -> dict:
    """Create a fresh draft plan and pin the session to it ('+ New plan')."""
    from app.modules.plan import service as plan_service
    s = _owned_session(session, user_id, session_id)
    p = plan_service.start_new_draft_plan(session, user_id, s)
    return plan_service.plan_dict(session, p)


def list_drafts(session: Session, user_id: uuid.UUID) -> dict:
    """Inactive (draft) plans the user can review/activate, each with its parts."""
    from app.modules.plan.models import Plan
    from app.modules.plan import service as plan_service
    plans = session.exec(select(Plan).where(
        Plan.created_for == user_id, Plan.active == False)  # noqa: E712
        .order_by(Plan.created_at.desc())).all()
    return {"plans": [plan_service.plan_dict(session, p) for p in plans]}
