"""Groq client pool: key rotation, client caching, and the fallback chain.

This is the connection layer — it knows how to *reach* a model and nothing about what
any agent asks it. No prompts, no domain schemas, no middleware stacks live here.

Lifted verbatim (behaviour-preserving) from the former
`meal_planner_agent/llm.py:89-138`.
"""
from __future__ import annotations

import itertools
from functools import lru_cache
from typing import Optional

from app.core.llm.settings import (
    GROQ_MODEL, GROQ_FALLBACK_MODEL, DEFAULT_TEMPERATURE, groq_api_keys,
)

# Round-robin cursor over the key pool. next() on a count is atomic under the GIL.
_key_cursor = itertools.count()


@lru_cache(maxsize=32)
def _client(api_key: str, model: str, temperature: float):
    from langchain_groq import ChatGroq
    return ChatGroq(model=model, temperature=temperature, api_key=api_key)


def llm_candidates(temperature: float = DEFAULT_TEMPERATURE) -> tuple:
    """Candidates for one request, in the order they'll be tried.

    Each request starts on the *next* key in the pool, so load spreads evenly instead of
    key1 absorbing everything. Ordering is model-outer/key-inner, so a rate-limited key
    fails over to the preferred model on another key before degrading to the fallback model:

        req #1 -> k1/main  k2/main  k3/main  k1/fb  k2/fb  k3/fb
        req #2 -> k2/main  k3/main  k1/main  k2/fb  k3/fb  k1/fb

    The ChatGroq clients themselves are cached per (key, model, temperature).
    """
    keys = groq_api_keys()
    start = next(_key_cursor) % len(keys)
    rotated = [keys[(start + i) % len(keys)] for i in range(len(keys))]
    return tuple(
        _client(key, model, temperature)
        for model in (GROQ_MODEL, GROQ_FALLBACK_MODEL)
        for key in rotated
    )


def chain(candidates):
    """First candidate with the rest attached as LangChain fallbacks."""
    cands = list(candidates)
    return cands[0].with_fallbacks(cands[1:]) if len(cands) > 1 else cands[0]


def model_chain(temperature: Optional[float] = None):
    """A ready-to-invoke chat model with the full key/model fallback chain attached."""
    return chain(llm_candidates(DEFAULT_TEMPERATURE if temperature is None else temperature))
