"""The setup chatbot.

Runs on LangChain's `create_agent`, replacing a hand-rolled tool loop
(`bind_tools` -> invoke -> check `.tool_calls` -> append `ToolMessage` -> repeat).

The agent is built **per request**, which is cheap: the underlying `ChatGroq` clients
are `lru_cache`d, so construction only re-wires already-warm objects. Building per
request is what keeps the API-key rotation working — `llm_candidates()` advances the
round-robin cursor on every call — and lets tools close over the request's DB session
exactly as they did before.
"""
from __future__ import annotations

import json
import logging
import re
import threading
from typing import Callable, Iterator, Optional

from langchain.agents import create_agent
from langchain_core.messages import AIMessage
from langchain_core.tools import StructuredTool

from app.core.llm import TokenUsageMiddleware
from app.core.llm.models import chain, llm_candidates
from app.agents.setup_chat.middleware import build_middleware

logger = logging.getLogger(__name__)


# ── Groq quirk: tool calls emitted as literal text ─────────────────────────
# Groq/Llama sometimes puts a tool call in `content` instead of `tool_calls`; with and
# without the closing tag have both been observed. create_agent handles the structured
# path, but this stays as an output guard so the syntax never reaches the user.
_INLINE_CALL_RE = re.compile(r"<function=(\w+)>\s*(\{.*?\})\s*</function>", re.DOTALL)
_INLINE_CALL_LOOSE_RE = re.compile(r"<function=(\w+)>\s*(\{[^<]*\})?", re.DOTALL)


def strip_inline_tool_calls(text: str) -> str:
    """Remove any tool-call syntax so it never reaches the user."""
    cleaned = _INLINE_CALL_RE.sub("", text or "")
    cleaned = _INLINE_CALL_LOOSE_RE.sub("", cleaned)
    return cleaned.replace("</function>", "").strip()


# ── Tool construction ──────────────────────────────────────────────────────

def build_tools(schemas: list[dict], registry: dict[str, Callable]) -> list[StructuredTool]:
    """Turn the OpenAI-format schemas + the DB-bound registry into agent tools.

    The registry functions already close over the request's session and user, and they
    return `{"error": ...}` dicts rather than raising — both behaviours are preserved.

    All tools from one request share ONE lock: when the model batches several tool
    calls into a single message, LangGraph's tool node executes them in parallel
    threads, but every registry function closes over the same SQLModel Session — which
    is not thread-safe. Unserialized, one call's commit() lands mid-flush of another
    ("Method 'commit()' can't be called here; '_prepare_impl()' is already in
    progress" / "This transaction is closed") and a whole batch of writes dies. The
    lock restores the old hand-rolled loop's sequential semantics.
    """
    lock = threading.Lock()
    tools: list[StructuredTool] = []
    for entry in schemas:
        fn_spec = entry["function"]
        name = fn_spec["name"]
        impl = registry.get(name)
        if impl is None:
            logger.warning("tool %s advertised but not in registry — skipping", name)
            continue
        tools.append(StructuredTool.from_function(
            func=_wrap(name, impl, lock),
            name=name,
            description=fn_spec.get("description", ""),
            args_schema=fn_spec.get("parameters") or {"type": "object", "properties": {}},
        ))
    return tools


def _wrap(name: str, impl: Callable, lock: threading.Lock) -> Callable:
    """Keep the old contract: tools return error dicts, they don't raise — and the
    result always reaches the model as a non-empty JSON *string*.

    That last part matters. The old hand-rolled loop built every ToolMessage as
    `json.dumps(result, default=str)`, so an empty result became the string "[]".
    StructuredTool instead passes the return value straight through, so a tool that
    returns `[]` produces a ToolMessage whose content is an empty list — which Groq
    rejects outright:

        400 'messages.N' : for 'role:tool' ... minimum number of items is 1

    `list_daily_goals`, `get_past_session_summaries` and `get_session_transcript` all
    return lists that are empty for a new user, so this fired on ordinary accounts.
    Serializing here restores the old behaviour exactly.
    """
    def _call(**kwargs):
        with lock:  # serialize: the shared DB session is not thread-safe (see build_tools)
            try:
                result = impl(**(kwargs or {}))
            except Exception as e:  # noqa: BLE001
                logger.warning("tool %s failed: %s", name, e)
                result = {"error": str(e)}
        try:
            return json.dumps(result, default=str)
        except (TypeError, ValueError):
            return json.dumps({"result": str(result)})
    _call.__name__ = name
    return _call


# ── Agent construction ─────────────────────────────────────────────────────

def build_agent(system_prompt: str, tools: list, *, tracker: TokenUsageMiddleware,
                summarize: bool = True, hitl: bool = False):
    """A per-request agent with the key/model fallback chain and this agent's middleware.

    `hitl=True` adds approval gating on write tools and attaches the Postgres
    checkpointer that `interrupt()` requires. The caller decides: it passes the
    session's `approval_mode` flag (user-toggled in the chat UI), so gating is
    per-chat rather than a deploy-wide env switch.
    """
    from app.agents.setup_chat import hitl as hitl_mod

    middleware = build_middleware(tracker=tracker, summarize=summarize)
    checkpointer = None
    if hitl:
        middleware.append(hitl_mod.build_hitl_middleware())
        checkpointer = hitl_mod.get_checkpointer()

    return create_agent(
        model=chain(llm_candidates()),
        tools=tools,
        system_prompt=system_prompt,
        middleware=middleware,
        checkpointer=checkpointer,
    )


# ── Streaming ──────────────────────────────────────────────────────────────

# Only the agent's own model node speaks to the user. Middleware that calls a model
# runs under its own node (e.g. "SummarizationMiddleware.before_model"), and those
# chunks must never be streamed — otherwise the summarizer's internal output
# ("## SESSION INTENT / ## SUMMARY / ## ARTIFACTS ...") is shown to the user as if it
# were the assistant's reply.
AGENT_MODEL_NODE = "model"

# `exit_behavior="end"` on ModelCallLimitMiddleware injects this as the assistant's
# message. It is diagnostic text, not something a user should ever read.
_LIMIT_MARKERS = ("model call limits exceeded", "call limit reached")


def is_limit_notice(text: str) -> bool:
    t = (text or "").strip().lower()
    return any(m in t for m in _LIMIT_MARKERS)


def stream_events(agent, agent_input, config: Optional[dict] = None) -> Iterator[dict]:
    """Yield `{"delta": str}` text events, with `{"reset": True}` between model messages.

    Why the reset exists: in a tool-using turn the model often narrates BEFORE its
    tool call ("Let me check your data…"), and those content chunks stream out before
    the tool-call chunks that would mark the message as skippable even arrive. With a
    plain append, every intermediate narration concatenates into one reply — the user
    sees "What's the target?……What duration would you like?……Just tell me the target…"
    — and that garbled blob is what gets persisted, poisoning the next turn's context.

    So: chunks are keyed by message id. A new id means a new model call started; the
    consumer discards what it buffered and starts over. Whatever survives at the end
    is exactly the final answer.

    `agent_input` is `{"messages": [...]}` for a normal turn or a `Command` on resume.

    Also filtered: chunks from nodes other than the agent's model node (middleware
    internals like the summarizer), chunks carrying tool-call fragments, and the
    model-call-limit notice.
    """
    if isinstance(agent_input, list):
        agent_input = {"messages": agent_input}
    current_id = None
    emitted = False
    for chunk, meta in agent.stream(agent_input, config=config or {},
                                    stream_mode="messages"):
        from langchain_core.messages import ToolMessage
        if isinstance(chunk, ToolMessage):
            yield {"tool": getattr(chunk, "name", "unknown"), "content": chunk.content}
            continue

        if (meta or {}).get("langgraph_node") != AGENT_MODEL_NODE:
            continue
        if not isinstance(chunk, AIMessage):
            continue
        cid = getattr(chunk, "id", None)
        if cid is not None and cid != current_id:
            if emitted:
                yield {"reset": True}
                emitted = False
            current_id = cid
        if getattr(chunk, "tool_calls", None) or getattr(chunk, "tool_call_chunks", None):
            continue
        piece = chunk.content
        if not piece:
            continue
        if isinstance(piece, list):  # some providers emit content blocks
            piece = "".join(b.get("text", "") for b in piece if isinstance(b, dict))
        if piece and not is_limit_notice(piece):
            emitted = True
            yield {"delta": piece}


