"""Structured output against the Groq pool.

Public replacement for the former private `meal_planner_agent/llm.py:_structured`,
which `enrichment.py` had to reach into across module boundaries.
"""
from __future__ import annotations

from typing import Optional

from app.core.llm.models import chain, llm_candidates
from app.core.llm.settings import DEFAULT_TEMPERATURE


def structured(schema, temperature: Optional[float] = None):
    """A runnable that returns `schema` (any Pydantic model), with the full
    key/model fallback chain attached.

    Bounds and enums declared on `schema` are enforced at parse time, so invalid model
    output raises instead of reaching the database.
    """
    cands = llm_candidates(DEFAULT_TEMPERATURE if temperature is None else temperature)
    return chain([c.with_structured_output(schema) for c in cands])
