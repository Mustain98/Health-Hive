"""Middleware stack owned by the setup chatbot.

Composed here, not shared. The other two agents are single-shot `response_format`
calls and deliberately get no middleware at all.

What each piece replaces:
  ModelCallLimitMiddleware  -> the hand-rolled `max_iters=4` in the old tool loop
  ToolRetryMiddleware       -> the bare try/except around each tool call
  SummarizationMiddleware   -> the hard session close at MAX_MESSAGES
  TokenUsageMiddleware      -> manual usage_metadata bookkeeping in the service
"""
from __future__ import annotations

import os

from langchain.agents.middleware import (
    ModelCallLimitMiddleware,
    SummarizationMiddleware,
    ToolRetryMiddleware,
)

from app.core.llm import TokenUsageMiddleware
from app.core.llm.models import model_chain

# How many times the model may be called in ONE user turn.
#
# This is NOT the same budget as the old hand-rolled loop's `max_iters=4`. That counted
# loop *iterations*, and each iteration could execute a whole batch of tool calls.
# ModelCallLimitMiddleware counts every model call, so 4 meant the agent gave up after
# roughly two tool round-trips — which is why "add these 10 daily goals" stopped partway
# and answered with the limit notice instead of finishing the work.
#
# A realistic worst case is one call to decide, one per write batch, and one to
# summarise back to the user. 25 leaves headroom for a 10-goal request without letting a
# genuinely looping agent run away.
MAX_MODEL_CALLS_PER_TURN = 25

# Summarize once the transcript passes this many messages, keeping the most recent
# KEEP_RECENT_MESSAGES verbatim. Message-count based for now; switch to
# ("tokens", N) once plan_setup_sessions has enough usage data to pick a budget.
SUMMARIZE_AFTER_MESSAGES = 30
KEEP_RECENT_MESSAGES = 10




def build_middleware(*, tracker: TokenUsageMiddleware, summarize: bool = True) -> list:
    """The setup chat's stack. Order matters: outermost first.

    Notes on the selector:
    - It filters what is *advertised* to the model, not what the tool node can
      execute — so a HITL resume of an already-approved call is unaffected.
    - Its own (small) selection call runs outside the agent's model node, so
      TokenUsageMiddleware does not count it; tracked usage undercounts slightly.
    """
    stack: list = [
        tracker,
        ModelCallLimitMiddleware(run_limit=MAX_MODEL_CALLS_PER_TURN, exit_behavior="end"),
        ToolRetryMiddleware(max_retries=2, on_failure="continue"),
    ]
    if summarize:
        stack.append(
            SummarizationMiddleware(
                model=model_chain(),
                trigger=("messages", SUMMARIZE_AFTER_MESSAGES),
                keep=("messages", KEEP_RECENT_MESSAGES),
            )
        )
    return stack
