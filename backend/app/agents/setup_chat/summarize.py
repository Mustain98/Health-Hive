"""Session summarization for the setup chat.

`SummarizationMiddleware` compresses the *in-flight* conversation so long chats keep
working. This module is the separate, durable summary written when a session closes —
the one shown as the session preview and offered to later chats via
`get_past_session_summaries`.
"""
from __future__ import annotations

import logging
from typing import List

from app.core.llm.models import model_chain
from app.agents.setup_chat.prompts import SUMMARIZE_SYSTEM

logger = logging.getLogger(__name__)


def summarize_session(history: List[dict]) -> str:
    """Short rolling-memory summary of a finished setup chat. Never raises."""
    convo = "\n".join(f"{m.get('role')}: {m.get('content','')}" for m in history)
    try:
        resp = model_chain().invoke([("system", SUMMARIZE_SYSTEM), ("human", convo)])
        return (getattr(resp, "content", None) or "").strip()
    except Exception as e:  # noqa: BLE001
        logger.warning("session summarize failed: %s", e)
        return ""
