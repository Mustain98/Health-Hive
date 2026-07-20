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
from app.core.llm import TokenUsageMiddleware
from app.agents.setup_chat.models import (
    PlanSetupSession, PlanSetupMessage, SetupSessionStatus, SetupRole, MAX_MESSAGES,
)
from app.agents.setup_chat import prompts
from app.agents.setup_chat import agent as agent_mod
from app.agents.setup_chat.summarize import summarize_session
from app.agents.setup_chat.finalize import setup_finalize
from app.agents.setup_chat import hitl
from app.agents.setup_chat import tools as setup_tools
from app.agents.meal_plan.service import assemble_profile, _coerce_meal_time
from app.utils.calculate import calculate_tdee

from app.modules.milestone.models import Milestone
from app.modules.nutrition_target.models import NutritionTarget
from app.modules.daily_goal.models import DailyGoal
from app.modules.meal_plan_setting.models import MealPlanSetting, MealPlanSettingTimedMeal
from app.modules.milestone.schemas import (
    MilestoneType, goal_type_for_milestone, validate_milestone_attributes,
)
from app.modules.daily_goal.schemas import (
    DailyGoalType, validate_daily_goal_attributes, validate_unit_for_type,
)
from app.modules.milestone.services import risk as milestone_risk
from app.modules.daily_goal.services import risk as daily_goal_risk
from app.utils.text import short
from app.modules.notification.services import notification as notif_service
from app.modules.notification.models import NotificationType

logger = logging.getLogger(__name__)


# ── Sessions & messages ─────────────────────────────────────────────────────

def start_session(session: Session, user_id: uuid.UUID) -> PlanSetupSession:
    # SETUP_CHAT_HITL only seeds the default; the user can flip approval_mode per chat.
    s = PlanSetupSession(user_id=user_id, approval_mode=hitl.hitl_default())
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
        "approval_mode": bool(s.approval_mode),
        "pending": bool(s.pending_thread_id),
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
            "approval_mode": bool(s.approval_mode),
        })
    return out


def set_approval_mode(session: Session, user_id: uuid.UUID, session_id: uuid.UUID,
                      on: bool) -> dict:
    """Flip "ask before saving" for one chat. Takes effect from the next turn — the
    agent is built per request, so no state needs invalidating. A run already suspended
    on an approval stays resumable regardless of later toggling (assert_resumable
    checks this same flag, so turning it off also declines further resumes)."""
    s = _owned_session(session, user_id, session_id)
    s.approval_mode = bool(on)
    session.add(s)
    session.commit()
    return get_session(session, user_id, session_id)


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


from app.agents.setup_chat.specialists import SPECIALISTS

def _spec_prompt(spec_name: str, reference_session_id: Optional[uuid.UUID]) -> str:
    """The system prompt for the chosen specialist.

    The draft-picker rule is appended centrally rather than pasted into all five specialist
    modules — every one of them can hit the guard.
    """
    prompt = SPECIALISTS[spec_name].PROMPT + prompts.DRAFT_PICKER_RULE
    if reference_session_id:
        prompt += (f"\n\nThe user is referencing an earlier chat (session id "
                   f"{reference_session_id}). Call get_session_transcript if you need its details.")
    return prompt


def _lc_messages(history: list[dict], reference_session_id: Optional[uuid.UUID] = None) -> list:
    """The conversation only — the system prompt is passed to the agent separately."""
    return [("ai" if m["role"] == "assistant" else "human", m["content"]) for m in history]


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
        
        from app.agents.setup_chat.turn_router import route_turn
        spec_name = route_turn(content)
        spec = SPECIALISTS[spec_name]
        
        # Guards append here when a write is blocked pending a draft-plan choice; read
        # after the turn commits (see the `choice` frame below).
        signals: list[dict] = []
        registry = setup_tools.build_tool_registry(db, user_id, reference_session_id,
                                                   setup_session_id=session_id, signals=signals)
        filtered_registry = {k: v for k, v in registry.items() if k in spec.TOOLS}
        tools = agent_mod.build_tools(setup_tools.TOOL_SCHEMAS, filtered_registry)

        tracker = TokenUsageMiddleware(label=f"setup_chat_{spec_name}")
        agent = agent_mod.build_agent(_spec_prompt(spec_name, reference_session_id), tools,
                                      tracker=tracker, hitl=bool(s.approval_mode))
        # A checkpointer thread is only needed when a run can suspend for approval —
        # and it is PER TURN, not per session. With a session-wide thread id, every
        # turn appended the full DB-rebuilt history to the same graph state, so the
        # thread ballooned turn over turn. A fresh thread per turn is seeded with
        # exactly the history we pass in; the DB transcript stays the source of truth.
        turn_thread = f"{session_id}:{s.message_count}"
        config = hitl.thread_config(turn_thread) if s.approval_mode else None
        if s.pending_thread_id:
            # The user typed a new message while an approval was pending: that stale
            # proposal is abandoned (its writes never ran) and this turn supersedes it.
            logger.info("[Setup] abandoning stale pending approval on %s", session_id)
            s.pending_thread_id = None
            db.add(s); db.commit()

        reply_parts: list[str] = []
        tool_events = []
        frame = None
        try:
            # Real token streaming — the model's answer is forwarded as it is produced,
            # replacing the old trick of generating the whole reply then slicing it into
            # 60-character chunks to look live. Tool-call chunks are filtered out by
            # stream_events, so arguments never reach the user.
            for ev in agent_mod.stream_events(agent, messages, config):
                if ev.get("reset"):
                    # A new model call started — everything streamed so far was
                    # narration before a tool call, not the answer. Drop it here and
                    # tell the client to clear the bubble.
                    reply_parts = []
                    yield _sse({"reset": True})
                    continue
                if "tool" in ev:
                    tool_events.append(ev)
                    continue
                piece = ev["delta"]
                cleaned = agent_mod.strip_inline_tool_calls(piece) if "<function=" in piece else piece
                if not cleaned:
                    continue
                reply_parts.append(cleaned)
                yield _sse({"delta": cleaned})
            
            # If a write tool paused for approval, tell the client what is pending.
            # The client answers via POST /sessions/{id}/resume.
            if config:  # set only when this session runs in approval mode
                frame = hitl.interrupt_frame(agent, config)
                if frame:
                    s.pending_thread_id = turn_thread  # resume finds the run here
                    yield _sse({"interrupt": frame})

            def _fallback_reply(tool_events: list[dict], pending_frame: Optional[dict]) -> str:
                if pending_frame:
                    n = sum(1 for req in pending_frame.get("requests", []) if not "batch_idx" in req or req["batch_idx"] == 0)
                    return f"I've proposed {n} change(s) — review them above."
                if not tool_events:
                    return "Sorry, could you rephrase that?"
                for ev in tool_events:
                    if "error" in str(ev.get("content", "")).lower():
                        return f"There was an error saving: {ev['content']} — here's a corrected version."
                return "I've processed your data."

            reply = "".join(reply_parts).strip() or _fallback_reply(tool_events, frame)
            if not reply_parts:
                yield _sse({"delta": reply})

        except Exception as e:  # noqa: BLE001
            logger.exception("[Setup] stream failed for session %s", session_id)
            msg = str(e).lower()
            if any(k in msg for k in ("context_length", "context length", "too large", "rate_limit", "rate limit")):
                reply = "This chat has gotten long — please start a new session to continue."
            else:
                reply = "I'm having trouble responding right now — please try again."
            yield _sse({"delta": reply})

        turn_usage = tracker.totals

        # Belt and braces. Tools roll back their own failures (see tools._fail), but if
        # anything still left this Session in a pending-rollback state, persisting the
        # transcript would raise PendingRollbackError and the user would lose the turn.
        # Recover once rather than failing the whole response.
        try:
            db.add(PlanSetupMessage(session_id=s.id, role=SetupRole.assistant, content=reply))
            db.flush()
        except Exception:  # noqa: BLE001
            logger.warning("[Setup] transcript write failed; retrying on a clean transaction (%s)",
                           session_id)
            db.rollback()
            s = db.get(PlanSetupSession, session_id)
            db.add(PlanSetupMessage(session_id=s.id, role=SetupRole.assistant, content=reply))
        s.message_count += 1
        s.total_input_tokens += turn_usage.input
        s.total_output_tokens += turn_usage.output
        s.llm_call_count += turn_usage.calls
        logger.info(
            "llm_usage label=setup_chat session=%s calls=%d input=%d output=%d "
            "session_total=%d",
            session_id, turn_usage.calls, turn_usage.input, turn_usage.output,
            s.total_input_tokens + s.total_output_tokens,
        )
        # The session no longer closes because the chat got long — SummarizationMiddleware
        # compresses the in-flight context so it keeps working. MAX_MESSAGES is now a cost
        # ceiling that is rarely reached, not a UX wall.
        if s.message_count >= MAX_MESSAGES:
            s.status = SetupSessionStatus.closed
            s.summary = summarize_session(_history(_messages(db, session_id)))
        db.add(s)
        db.commit()

        # A write blocked on "which draft plan?" — hand the client the clickable slots.
        # Emitted AFTER the commit so the re-resolve reads committed state (a tool may have
        # pinned a plan mid-turn) and a picker can never appear for a turn that isn't in the
        # transcript. Suppressed when an approval card is already up: that takes precedence,
        # and resume_turn re-checks on the way through.
        if not frame:
            choice = _choice_frame(db, user_id, session_id, signals)
            if choice:
                yield _sse({"choice": choice})

        yield _sse({
            "done": True,
            "message_count": s.message_count,
            "limit_reached": s.message_count >= MAX_MESSAGES,
            "status": s.status.value if hasattr(s.status, "value") else s.status,
        })


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj, default=str)}\n\n"


def _choice_frame(db: Session, user_id: uuid.UUID, session_id: uuid.UUID,
                  signals: list) -> Optional[dict]:
    """The `{"choice": …}` payload for the LAST recorded draft-choice signal, re-resolved
    against committed state — or None when nothing needs picking.

    Last, not first: a refused model often retries and appends an identical record.
    """
    sig = next((s for s in reversed(signals) if s.get("kind") == setup_tools.CHOICE_KIND), None)
    return setup_tools.resolve_choice_signal(db, user_id, session_id, sig) if sig else None


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
        draft = setup_finalize(profile, history, tdee)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"Couldn't produce a valid setup: {e}. Try refining the chat.")

    # 2) Build (unsaved) milestone + daily goals for the risk guard.
    # milestone_type is already a MilestoneType — the structured-output schema
    # enforces it, so no string coercion (and no 422 path) is needed here.
    mtype = draft.milestone.milestone_type

    goal = Milestone(
        created_for=user_id, created_by=user_id, active=False,
        goal_type=goal_type_for_milestone(mtype),
        milestone_type=mtype, name=short(draft.milestone.name, 120),
        target_weight=draft.milestone.target_weight, target_value=draft.milestone.target_value,
        # NB: do NOT wrap units in short() — str() on a str-Enum yields
        # "MilestoneUnit.kg", not "kg". The enum is already length-bounded.
        unit=draft.milestone.unit, duration_days=draft.milestone.duration_days,
        attributes=validate_milestone_attributes(mtype, draft.milestone.attributes),
    )

    daily_goals: list[DailyGoal] = []
    for dg in draft.daily_goals[:5]:  # cap: don't dump a whole exercise program
        gt = dg.goal_type  # already a DailyGoalType via the structured-output schema
        try:
            # Rejects a unit that is valid in isolation but wrong for this goal type
            # (e.g. `steps` on a calorie_burn goal).
            unit = validate_unit_for_type(gt, dg.unit)
            attributes = validate_daily_goal_attributes(gt, dg.attributes)
        except ValueError:
            continue  # skip the malformed goal rather than fail the whole finalize
        daily_goals.append(DailyGoal(
            created_for=user_id, created_by=user_id, active=False,
            goal_type=gt, name=short(dg.name, 120), target_value=dg.target_value,
            unit=unit,  # enum — never short()
            attributes=attributes,
        ))

    # 3) Risk guard — AI must not produce unsafe drafts; refer to a consultant instead.
    reasons = [r for r in (
        milestone_risk.is_risky_milestone(session, user_id, goal),
        *[daily_goal_risk.is_risky_daily_goal(session, user_id, d) for d in daily_goals],
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
    from app.modules.plan import services as plan_service
    s = _owned_session(session, user_id, session_id)
    p = plan_service.pin_session_draft_plan(session, user_id, s, plan_id)
    return plan_service.plan_dict(session, p)


def new_draft_plan(session: Session, user_id: uuid.UUID, session_id: uuid.UUID) -> dict:
    """Create a fresh draft plan and pin the session to it ('+ New plan')."""
    from app.modules.plan import services as plan_service
    s = _owned_session(session, user_id, session_id)
    p = plan_service.start_new_draft_plan(session, user_id, s)
    return plan_service.plan_dict(session, p)


def list_drafts(session: Session, user_id: uuid.UUID) -> dict:
    """Inactive (draft) plans the user can review/activate, each with its parts."""
    from app.modules.plan.models import Plan
    from app.modules.plan import services as plan_service
    plans = session.exec(select(Plan).where(
        Plan.created_for == user_id, Plan.active == False)  # noqa: E712
        .order_by(Plan.created_at.desc())).all()
    return {"plans": [plan_service.plan_dict(session, p) for p in plans]}


# ── Human-in-the-loop resume ───────────────────────────────────────────────

def assert_resumable(session: Session, user_id: uuid.UUID, session_id: uuid.UUID) -> None:
    """Clean HTTP errors before the SSE stream opens."""
    s = _owned_session(session, user_id, session_id)
    if not s.pending_thread_id:
        raise HTTPException(status_code=409,
                            detail="Nothing is awaiting approval on this chat.")
    if s.status == SetupSessionStatus.closed:
        raise HTTPException(status_code=409, detail="This session is closed.")


def _item_label(tool: str, args: dict) -> str:
    """Human-readable label for one pending item, e.g. 'daily goal "Back Squat"'."""
    kind = tool.replace("add_", "").replace("set_", "").replace("delete_", "delete ")
    name = (args or {}).get("name")
    return f'{kind.replace("_", " ")} "{name}"' if name else kind.replace("_", " ")


def _decision_summary(pending: list[dict], decisions: list[dict]) -> str:
    """The transcript record of what the user decided — THE memory that stops the
    agent from re-proposing rejected items in later turns. Persisted as a user message."""
    saved, edited, rejected = [], [], []
    for req, d in zip(pending, decisions):
        label = _item_label(req["tool"], req.get("args") or {})
        note = (d.get("message") or "").strip()
        if d["decision"] == "approve":
            saved.append(label)
        elif d["decision"] == "edit":
            edited.append(f"{label} — change: {note}")
        else:
            rejected.append(f"{label}{' — ' + note if note else ''}")
    parts = []
    if saved:
        parts.append("Approved and saved: " + "; ".join(saved) + ".")
    if edited:
        parts.append("Requested changes (re-propose corrected): " + "; ".join(edited) + ".")
    if rejected:
        parts.append("Rejected (do not propose these again unchanged): " + "; ".join(rejected) + ".")
    return " ".join(parts) or "Reviewed the proposal."


def resume_turn(user_id: uuid.UUID, session_id: uuid.UUID,
                decisions_in: list[dict]) -> Iterator[str]:
    """Apply the user's per-item decisions to a run suspended on write-tool approvals.

    `decisions_in`: [{"decision": "approve"|"edit"|"reject", "message"?: str}, ...],
    index-matched to the pending requests the UI displayed.

    Semantics (user-facing):
      approve — finalize this item as proposed.
      edit    — keep the idea, re-propose it corrected per the note. Mapped to the
                middleware's reject-with-message: a mechanical `edit` needs literal
                args, but the user speaks in natural language, so the model applies
                the correction and raises a fresh approval for the corrected item.
      reject  — too much wrong; drop it or propose something substantially different.

    Mixed decisions in one call are the point: approved items execute exactly once
    (add_daily_goal upserts by type+name, so re-proposals cannot duplicate), while
    edited/rejected ones stay in the same run with the feedback attached — nothing
    is silently dropped.
    """
    from langgraph.types import Command

    with Session(engine) as db:
        s = db.get(PlanSetupSession, session_id)
        if not s or s.user_id != user_id:
            yield _sse({"error": "session not found"}); return
        if not s.pending_thread_id:
            yield _sse({"error": "nothing is awaiting approval on this chat"}); return

        history = _messages(db, session_id)
        last_user_msg = next((m.content for m in reversed(history) if m.role == SetupRole.user), "")
        from app.agents.setup_chat.turn_router import route_turn
        spec_name = route_turn(last_user_msg)
        spec = SPECIALISTS[spec_name]
        
        signals: list[dict] = []
        registry = setup_tools.build_tool_registry(db, user_id, None, setup_session_id=session_id,
                                                   signals=signals)
        filtered_registry = {k: v for k, v in registry.items() if k in spec.TOOLS}
        tools = agent_mod.build_tools(setup_tools.TOOL_SCHEMAS, filtered_registry)
        
        tracker = TokenUsageMiddleware(label=f"setup_chat_resume_{spec_name}")
        agent = agent_mod.build_agent(_spec_prompt(spec_name, None), tools, tracker=tracker, hitl=True)
        config = hitl.thread_config(s.pending_thread_id)

        pending = hitl.pending_requests(agent, config)
        if not pending:
            s.pending_thread_id = None
            db.add(s); db.commit()
            yield _sse({"error": "nothing is awaiting approval on this chat"}); return
        if len(decisions_in) != len(pending):
            yield _sse({"error": f"expected {len(pending)} decisions, got {len(decisions_in)} — "
                                 "the proposal may have changed; reload the chat"}); return

        # The approval path bypasses the propose_plan_changes guard entirely: HITL interrupts
        # before the tool body runs, and the approved items below are executed by calling the
        # UNROLLED LEAF tools (set_nutrition_target, add_daily_goal, …) straight out of the
        # registry. Those reach get_or_create_session_draft_plan, which silently adopts or
        # creates a plan — so without this pre-check, approving in an unpinned chat writes into
        # an arbitrary plan and the user is never asked. Hence an explicit check here rather
        # than a signal: there is no guard left to append one.
        if any(d["decision"] == "approve" for d in decisions_in):
            sig = setup_tools.draft_choice_signal(db, user_id, session_id,
                                                  reason="unpinned_with_drafts")
            if sig:
                # Nothing is consumed: pending_thread_id and the suspended graph stay put, so
                # the SAME decisions replay verbatim once the user picks (and the
                # len(decisions) == len(pending) check above still passes on the second POST).
                sig["resume"] = {"decisions": decisions_in}
                msg = "Which draft plan should I save these into? Pick one below."
                db.add(PlanSetupMessage(session_id=s.id, role=SetupRole.assistant, content=msg))
                s.message_count += 1
                db.add(s); db.commit()
                yield _sse({"delta": msg})
                yield _sse({"choice": sig})
                yield _sse({
                    "done": True,
                    "message_count": s.message_count,
                    "limit_reached": s.message_count >= MAX_MESSAGES,
                    "status": s.status.value if hasattr(s.status, "value") else s.status,
                })
                return

        # Map UI decisions onto the middleware's protocol.
        # Since we unrolled batch tools (like propose_plan_changes) into multiple UI rows,
        # we must re-roll them back into one decision per original action request.
        # We group by req_idx (the index of the action request in the middleware's HITLRequest).
        
        # We need the tools registry to execute batch items manually.
        registry = setup_tools.build_tool_registry(db, user_id, None, setup_session_id=session_id)
        
        grouped_decisions = {}
        grouped_pending = {}
        for req, d in zip(pending, decisions_in):
            req_idx = req.get("req_idx", 0)
            grouped_decisions.setdefault(req_idx, []).append(d)
            grouped_pending.setdefault(req_idx, []).append(req)

        decisions = []
        # Re-roll into the exact number of decisions the middleware expects
        # (It expects len(decisions) == len(action_requests) which should equal len(grouped_decisions))
        for req_idx in sorted(grouped_decisions.keys()):
            ds = grouped_decisions[req_idx]
            reqs = grouped_pending[req_idx]
            
            is_batched = any("batch_idx" in r for r in reqs)
            
            if is_batched:
                n_saved = 0
                feedback_parts = []
                for r, d in zip(reqs, ds):
                    kind = d["decision"]
                    note = (d.get("message") or "").strip()
                    desc = r.get("description", r.get("tool"))
                    
                    if kind == "approve":
                        # Execute manually
                        fn = registry.get(r["tool"])
                        if fn:
                            try:
                                fn(**r["args"])
                                n_saved += 1
                            except Exception as e:
                                feedback_parts.append(f"- Failed to save {desc}: {e}")
                    elif kind == "edit":
                        feedback_parts.append(f"- {desc} needs correction: {note}. Re-propose it.")
                    else:
                        feedback_parts.append(f"- {desc} was rejected" + (f": {note}" if note else "") + ".")
                
                if not feedback_parts:
                    msg = f"Saved {n_saved} item(s) successfully."
                else:
                    msg = f"Saved {n_saved} item(s). Feedback on the rest:\n" + "\n".join(feedback_parts)
                # Send respond so the middleware skips executing propose_plan_changes
                decisions.append({"type": "respond", "message": msg})
            else:
                # Traditional 1-to-1 processing
                d = ds[0]
                kind = d["decision"]
                note = (d.get("message") or "").strip()
                if kind == "approve":
                    decisions.append({"type": "approve"})
                elif kind == "edit":
                    decisions.append({"type": "reject", "message":
                        f"Do NOT run this as-is. Re-propose this exact item corrected per the "
                        f"user's instruction, then request approval again: {note}"})
                else:
                    decisions.append({"type": "reject", "message":
                        "The user rejected this item outright"
                        + (f": {note}" if note else "")
                        + ". Do not propose it again unchanged."})

        # Persist the decisions BEFORE streaming, as a user-role message: this is the
        # cross-turn memory. In-run, the reject messages above ride in the graph
        # thread; across turns, the rebuilt history carries this line.
        db.add(PlanSetupMessage(session_id=s.id, role=SetupRole.user,
                                content=_decision_summary(pending, decisions_in)))
        s.message_count += 1
        db.commit()

        n_saved = sum(1 for d in decisions_in if d["decision"] == "approve")
        n_redo = len(decisions_in) - n_saved

        reply_parts: list[str] = []
        tool_events = []
        follow_up = None
        try:
            for ev in agent_mod.stream_events(agent, Command(resume={"decisions": decisions}),
                                              config):
                if ev.get("reset"):
                    reply_parts = []
                    yield _sse({"reset": True})
                    continue
                if "tool" in ev:
                    tool_events.append(ev)
                    continue
                reply_parts.append(ev["delta"])
                yield _sse({"delta": ev["delta"]})
            
            follow_up = hitl.interrupt_frame(agent, config)

            def _fallback_reply(tool_events: list[dict], pending_frame: Optional[dict]) -> str:
                if pending_frame:
                    n = sum(1 for req in pending_frame.get("requests", []) if not "batch_idx" in req or req["batch_idx"] == 0)
                    return f"I've proposed {n} change(s) — review them above."
                if not tool_events:
                    return f"Saved {n_saved} item(s)." if n_saved and not n_redo else f"Saved {n_saved}; reworking {n_redo} per your notes." if n_saved else "Okay — reworking that per your notes." if n_redo else "Done."
                for ev in tool_events:
                    if "error" in str(ev.get("content", "")).lower():
                        return f"There was an error saving: {ev['content']} — here's a corrected version."
                return "I've processed your data."

            reply = "".join(reply_parts).strip() or _fallback_reply(tool_events, follow_up)
            if not reply_parts:
                yield _sse({"delta": reply})
            
            # Edited/rejected items usually re-surface as a fresh approval in the SAME
            # thread. Emit it and keep pending_thread_id so the next resume finds it.
            if follow_up:
                yield _sse({"interrupt": follow_up})
        except Exception:  # noqa: BLE001
            logger.exception("[Setup] resume failed for session %s", session_id)
            reply = "I couldn't apply those decisions — please try again."
            yield _sse({"delta": reply})

        if not follow_up:
            s.pending_thread_id = None
        db.add(PlanSetupMessage(session_id=s.id, role=SetupRole.assistant, content=reply))
        s.message_count += 1
        s.total_input_tokens += tracker.totals.input
        s.total_output_tokens += tracker.totals.output
        s.llm_call_count += tracker.totals.calls
        db.add(s); db.commit()

        # The model may have called propose_plan_changes again on its way out and hit the
        # guard. Same precedence as stream_turn: a fresh approval card wins over a picker.
        if not follow_up:
            choice = _choice_frame(db, user_id, session_id, signals)
            if choice:
                yield _sse({"choice": choice})

        yield _sse({
            "done": True,
            "message_count": s.message_count,
            "limit_reached": s.message_count >= MAX_MESSAGES,
            "status": s.status.value if hasattr(s.status, "value") else s.status,
        })

