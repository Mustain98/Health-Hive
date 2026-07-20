"""Human-in-the-loop approval for the setup chat's write tools.

The agent may read freely, but every tool that writes a draft pauses for the user to
accept / edit / reject it.

**Disabled by default.** Set `SETUP_CHAT_HITL=1` to enable. The reason is a hard
dependency on the client: an interrupt suspends the graph and the run only continues
when someone POSTs a decision to `/sessions/{id}/resume`. A frontend that does not
know about the `interrupt` SSE event will simply appear to hang on any write. Turn
this on only once the UI handles that event.

Mechanically this needs durable graph state — `interrupt()` suspends mid-run and the
run is resumed later, possibly in a different process — so it requires a checkpointer.
`plan_setup_messages` cannot serve that role: it stores the transcript, not the
in-flight graph. The checkpointer holds only the suspended run; the transcript remains
the source of truth for the conversation.
"""
from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Optional

logger = logging.getLogger(__name__)


def hitl_default() -> bool:
    """Default `approval_mode` for NEWLY CREATED sessions.

    Activation is per-session now (`PlanSetupSession.approval_mode`, toggled from the
    chat UI); SETUP_CHAT_HITL only decides what a fresh session starts as. Turn-time
    code must gate on the session's flag, never on this.
    """
    return (os.getenv("SETUP_CHAT_HITL") or "").strip().lower() in ("1", "true", "yes", "on")


# The single batch tool that mutates a draft. Reads are never interrupted — pausing on
# `get_health_data` would make the chat unusable.
def interrupt_config() -> dict:
    """`interrupt_on` map for HumanInTheLoopMiddleware."""
    return {
        "propose_plan_changes": {
            # "respond" lets us bypass middleware's automatic execution and handle the 
            # unrolled batch execution manually in service.py
            "allowed_decisions": ["respond", "approve", "reject"], 
            "description": "The assistant proposed batch plan changes. Review the values before saving.",
        }
    }


def build_hitl_middleware():
    from langchain.agents.middleware import HumanInTheLoopMiddleware
    return HumanInTheLoopMiddleware(
        interrupt_on=interrupt_config(),
        description_prefix="Approve this change to your plan",
    )


# ── Checkpointer ───────────────────────────────────────────────────────────

def checkpointer_url() -> str:
    """Connection string for the checkpointer.

    `CHECKPOINTER_DATABASE_URL` overrides `DATABASE_URL`, which matters on Supabase:
    the **transaction** pooler (port 6543) does not support prepared statements or
    pipeline mode, and the checkpointer uses both. Symptom is

        psycopg.errors.DuplicatePreparedStatement: prepared statement "_pg3_0" already exists

    Point this at the session pooler / direct connection (port 5432) if you hit that.
    """
    url = os.getenv("CHECKPOINTER_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    # psycopg3 wants postgresql://, not the SQLAlchemy psycopg2 dialect form.
    return url.replace("postgresql+psycopg2://", "postgresql://")


@lru_cache(maxsize=1)
def _saver():
    """Process-wide PostgresSaver over the app's database.

    NB: `setup()` (which creates the checkpoint tables) is NOT called here — see
    `ensure_checkpoint_tables`. Table creation is an explicit, deliberate step.
    """
    from langgraph.checkpoint.postgres import PostgresSaver
    from psycopg_pool import ConnectionPool

    pool = ConnectionPool(
        conninfo=checkpointer_url(),
        max_size=5,
        open=True,
        kwargs={
            "autocommit": True,
            # None disables prepared statements. 0 would mean "prepare on first use",
            # which is exactly what a transaction pooler cannot handle.
            "prepare_threshold": None,
        },
    )
    # pipe=False: pipeline mode is also unsupported by transaction poolers.
    return PostgresSaver(pool, pipe=None)


def get_checkpointer():
    """The Postgres checkpointer `interrupt()` requires.

    No longer gated on the env var — any session may have approval_mode on, so this
    builds (lazily, `_saver` is cached) whenever such a session runs a turn. The
    checkpoint tables already exist; `ensure_checkpoint_tables()` remains the explicit
    setup step for fresh databases.
    """
    return _saver()


def ensure_checkpoint_tables() -> None:
    """Create the LangGraph checkpoint tables. Run once, deliberately — not on import."""
    _saver().setup()
    logger.info("langgraph checkpoint tables ensured")


def thread_config(session_id) -> dict:
    """One graph thread per setup session, so a suspended run resumes on the right chat."""
    return {"configurable": {"thread_id": str(session_id)}}


def pending_requests(agent, config) -> list[dict]:
    """Tool calls currently awaiting approval, in the order the agent proposed them.

    The middleware's interrupt value looks like:

        {"action_requests": [{"name": ..., "args": {...}, "description": ...}, ...],
         "review_configs":  [{"action_name": ..., "allowed_decisions": [...]}, ...]}

    This flattens it into one stable record per request so neither the SSE contract nor
    the UI depends on that internal shape.
    """
    try:
        state = agent.get_state(config)
    except Exception:  # noqa: BLE001
        logger.exception("could not read agent state for pending approvals")
        return []

    out: list[dict] = []
    for intr in (getattr(state, "interrupts", None) or []):
        value = getattr(intr, "value", intr) or {}
        if not isinstance(value, dict):
            continue
        requests = value.get("action_requests") or []
        configs = value.get("review_configs") or []
        by_name = {c.get("action_name"): c for c in configs if isinstance(c, dict)}
        for req_idx, req in enumerate(requests):
            if not isinstance(req, dict):
                continue
            name = req.get("name")
            if name == "propose_plan_changes":
                # Unroll the batch into individual UI items
                items = req.get("args", {}).get("items", [])
                for idx, item in enumerate(items):
                    kind = item.get("kind")
                    op = item.get("op", "set")
                    tool = f"{op}_{kind}"
                    if tool == "set_daily_goal":
                        tool = "add_daily_goal" if "daily_goal_id" not in item else "update_daily_goal"
                    
                    # Decisions for individual unrolled items
                    allowed = ["approve", "reject"] if op == "delete" else ["approve", "edit", "reject"]
                    
                    out.append({
                        "interrupt_id": getattr(intr, "id", None),
                        "req_idx": req_idx, # The action request index
                        "batch_idx": idx,  # Keep track of which item in the batch this is
                        "tool": tool,
                        "args": item,
                        "description": f"The assistant wants to {op} a {kind}.",
                        "allowed": allowed,
                    })
            else:
                cfg = by_name.get(name, {})
                out.append({
                    "interrupt_id": getattr(intr, "id", None),
                    "req_idx": req_idx,
                    "tool": name,
                    "args": req.get("args") or {},
                    "description": req.get("description"),
                    "allowed": cfg.get("allowed_decisions") or ["approve", "reject"],
                })
    return out


def interrupt_frame(agent, config) -> Optional[dict]:
    """The `{"interrupt": …}` SSE payload, or None when nothing is pending."""
    reqs = pending_requests(agent, config)
    return {"requests": reqs} if reqs else None
