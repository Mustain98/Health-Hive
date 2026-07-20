"""Jina embeddings HTTP client.

Connection layer only — it turns text into vectors and knows nothing about meals.
Meal indexing and pgvector retrieval stay with the meal-plan agent.

Callers should treat `EmbeddingUnavailable` as "degrade gracefully", not "fail the
request": the meal pipeline falls back to non-semantic retrieval when it is raised.
"""
from __future__ import annotations

import hashlib
import logging
import os
from typing import List

import httpx

from app.core.llm.settings import (
    EMBED_MODEL, JINA_URL, EMBED_BATCH_SIZE, EMBED_TIMEOUT_SECONDS,
)

logger = logging.getLogger(__name__)


class EmbeddingUnavailable(RuntimeError):
    """Raised when the Jina API can't serve embeddings (missing key, network, HTTP error)."""


def text_hash(text: str) -> str:
    """Stable content hash, used as a cache/staleness key."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _jina_embed(texts: List[str], task: str, dimensions: int) -> List[List[float]]:
    api_key = os.getenv("JINA_API_KEY")
    if not api_key:
        raise EmbeddingUnavailable("JINA_API_KEY not set")

    out: List[List[float]] = []
    try:
        for i in range(0, len(texts), EMBED_BATCH_SIZE):
            resp = httpx.post(
                JINA_URL,
                timeout=EMBED_TIMEOUT_SECONDS,
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": EMBED_MODEL,
                    "task": task,
                    "dimensions": dimensions,
                    "input": texts[i : i + EMBED_BATCH_SIZE],
                },
            )
            resp.raise_for_status()
            data = sorted(resp.json()["data"], key=lambda d: d["index"])
            out.extend(d["embedding"] for d in data)
    except httpx.HTTPError as exc:
        raise EmbeddingUnavailable(f"Jina embeddings request failed: {exc}") from exc
    return out


def embed_documents(texts: List[str], dimensions: int) -> List[List[float]]:
    """Embed passages for indexing."""
    return _jina_embed(texts, "retrieval.passage", dimensions)


def embed_query(text: str, dimensions: int) -> List[float]:
    """Embed a single query for retrieval."""
    return _jina_embed([text], "retrieval.query", dimensions)[0]
