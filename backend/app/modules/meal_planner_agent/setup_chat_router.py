import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from app.core.database import get_session
from app.core.auth import get_current_user
from app.modules.user.models import User
from app.modules.meal_planner_agent import setup_chat_service as svc

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
    ref_uuid = uuid.UUID(ref) if ref else None
    svc.validate_turn(session, me.id, session_id, content)  # raises clean HTTP errors
    return StreamingResponse(
        svc.stream_turn(me.id, session_id, content, ref_uuid),
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
