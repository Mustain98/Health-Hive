"""Token-usage accounting.

A generic `AgentMiddleware` that records how many tokens each model call consumed.
It knows nothing about any domain — it only reads `usage_metadata` off the response —
so it is a building block an agent may opt into, not part of a shared stack.

Why it exists: there is currently no data on how many tokens a setup chat actually
burns, so `SummarizationMiddleware` cannot be given a sensible token threshold and the
session cap is a guess. Record real usage first, then set limits from it.

Usage:

    tracker = TokenUsageMiddleware()
    agent = create_agent(model, tools=..., middleware=[tracker, ...])
    ...
    tracker.totals   # -> TokenUsage(input=..., output=..., calls=...)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from langchain.agents.middleware import AgentMiddleware

logger = logging.getLogger(__name__)


@dataclass
class TokenUsage:
    input: int = 0
    output: int = 0
    calls: int = 0

    @property
    def total(self) -> int:
        return self.input + self.output

    def add(self, input_tokens: int, output_tokens: int) -> None:
        self.input += input_tokens
        self.output += output_tokens
        self.calls += 1


def usage_of(message) -> tuple[int, int]:
    """(input_tokens, output_tokens) from a message, or (0, 0) if unreported.

    Providers are inconsistent about populating `usage_metadata`; missing counts are
    treated as zero rather than raising, so accounting never breaks a chat turn.
    """
    md = getattr(message, "usage_metadata", None) or {}
    return int(md.get("input_tokens") or 0), int(md.get("output_tokens") or 0)


@dataclass
class TokenUsageMiddleware(AgentMiddleware):
    """Accumulates token usage across every model call in one agent run."""

    label: str = "agent"
    totals: TokenUsage = field(default_factory=TokenUsage)

    def wrap_model_call(self, request, handler):
        response = handler(request)
        for msg in getattr(response, "result", None) or []:
            inp, out = usage_of(msg)
            if inp or out:
                self.totals.add(inp, out)
        return response

    async def awrap_model_call(self, request, handler):
        response = await handler(request)
        for msg in getattr(response, "result", None) or []:
            inp, out = usage_of(msg)
            if inp or out:
                self.totals.add(inp, out)
        return response

    def log(self, **context) -> None:
        """Emit one structured line. Call once per run, after the agent finishes."""
        logger.info(
            "llm_usage label=%s calls=%d input=%d output=%d total=%d%s",
            self.label, self.totals.calls, self.totals.input, self.totals.output,
            self.totals.total,
            "".join(f" {k}={v}" for k, v in context.items()),
        )
