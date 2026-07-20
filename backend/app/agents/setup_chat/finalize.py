"""Turn the conversation into structured, bounded drafts.

A single-shot structured-output call, separate from the conversational agent: the
schema is strict so invalid model output raises here rather than reaching the database.
Deliberately has NO fallback — a malformed finalize must fail loudly (the caller turns
it into a 422 and asks the user to refine the chat), unlike the meal-plan path where a
deterministic fallback is preferable to no plan at all.
"""
from __future__ import annotations

import json
from typing import List, Optional

from app.core.llm import structured
from app.agents.setup_chat.prompts import FINALIZE_SYSTEM
from app.agents.setup_chat.schemas import SetupFinalize


def setup_finalize(profile: dict, history: List[dict], tdee: Optional[int] = None) -> SetupFinalize:
    """Raises on invalid output — see module docstring."""
    convo = "\n".join(f"{m.get('role')}: {m.get('content','')}" for m in history)
    user_msg = (
        f"User data:\n{json.dumps(profile, default=str, indent=2)}\n\n"
        f"Estimated TDEE (kcal/day): {tdee}\n\n"
        f"Conversation so far:\n{convo}\n\n"
        "Return the finalized drafts."
    )
    return structured(SetupFinalize).invoke(
        [("system", FINALIZE_SYSTEM), ("human", user_msg)]
    )
