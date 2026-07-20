import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from app.core.database import get_session
from app.core.auth import get_current_user
from app.modules.user.models import User
from app.agents.setup_chat import service as svc

router = APIRouter(prefix="/plan-setup", tags=["Plan Setup Chatbot"])


@router.get("/sessions")
def list_sessions(
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    return svc.list_sessions(session, me.id)


@router.post("/sessions")
def start_session(
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    s = svc.start_session(session, me.id)
    return svc.get_session(session, me.id, s.id)


@router.get("/sessions/{session_id}")
def get_session_detail(
    session_id: uuid.UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    return svc.get_session(session, me.id, session_id)


@router.patch("/sessions/{session_id}")
def update_session(
    session_id: uuid.UUID,
    body: dict,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """Per-chat settings. Currently one: {"approval_mode": bool} — "ask before saving"."""
    if not isinstance((body or {}).get("approval_mode"), bool):
        raise HTTPException(status_code=422, detail="approval_mode (boolean) is required")
    return svc.set_approval_mode(session, me.id, session_id, body["approval_mode"])


@router.post("/sessions/{session_id}/messages")
def post_message(
    session_id: uuid.UUID,
    body: dict,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """Streams the assistant reply as SSE. Validates synchronously first so 4xx errors
    are returned cleanly before the stream starts."""
    content = (body or {}).get("content", "")
    ref = (body or {}).get("reference_session_id")
    try:
        ref_uuid = uuid.UUID(ref) if ref else None
    except (ValueError, TypeError):
        # Was an uncaught ValueError -> 500; a malformed id is a client error.
        raise HTTPException(status_code=422, detail="reference_session_id must be a uuid")
    svc.validate_turn(session, me.id, session_id, content)  # raises clean HTTP errors
    return StreamingResponse(
        svc.stream_turn(me.id, session_id, content, ref_uuid),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/sessions/{session_id}/resume")
def resume(
    session_id: uuid.UUID,
    body: dict,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """Answer a pending approval with PER-ITEM decisions and continue the run.

    Body: {"decisions": [{"decision": "approve"|"edit"|"reject", "message"?: str}, ...]}
    — one entry per pending item, in the order the interrupt frame listed them.
    "edit" requires a message (the natural-language instruction of what to change);
    "reject" may carry one (why — it stops the agent re-proposing the same thing).
    """
    decisions = (body or {}).get("decisions")
    if not isinstance(decisions, list) or not decisions:
        raise HTTPException(status_code=422, detail="decisions must be a non-empty list")
    for i, d in enumerate(decisions):
        if not isinstance(d, dict) or d.get("decision") not in ("approve", "edit", "reject"):
            raise HTTPException(status_code=422,
                                detail=f"decisions[{i}].decision must be approve, edit or reject")
        if d["decision"] == "edit" and not (d.get("message") or "").strip():
            raise HTTPException(status_code=422,
                                detail=f"decisions[{i}]: edit requires a message saying what to change")
    svc.assert_resumable(session, me.id, session_id)
    return StreamingResponse(
        svc.resume_turn(me.id, session_id, decisions),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/sessions/{session_id}/finalize")
def finalize(
    session_id: uuid.UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    try:
        return svc.finalize(session, me.id, session_id)
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Finalize failed: {str(e)}")


@router.patch("/sessions/{session_id}/draft-plan")
def pin_draft_plan(
    session_id: uuid.UUID,
    body: dict,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """Point this chat at an existing inactive draft plan ('Continue editing')."""
    raw = (body or {}).get("plan_id")
    if not raw:
        raise HTTPException(status_code=400, detail="plan_id is required")
    try:
        plan_id = uuid.UUID(str(raw))
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="invalid plan_id")
    return svc.pin_draft_plan(session, me.id, session_id, plan_id)


@router.post("/sessions/{session_id}/new-draft-plan")
def new_draft_plan(
    session_id: uuid.UUID,
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    """Start a fresh draft plan for this chat ('+ New plan')."""
    return svc.new_draft_plan(session, me.id, session_id)


@router.get("/drafts")
def list_drafts(
    session: Session = Depends(get_session),
    me: User = Depends(get_current_user),
):
    return svc.list_drafts(session, me.id)
