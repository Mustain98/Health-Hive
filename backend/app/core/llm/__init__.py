"""LLM connection layer.

Everything here is domain-free: how to reach Groq, and how to ask for structured
output. Prompts, tools, response schemas and middleware stacks belong to the agent
that uses them — see `app/agents/`.
"""
from app.core.llm.models import llm_candidates, chain, model_chain
from app.core.llm.structured import structured
from app.core.llm.token_usage import TokenUsage, TokenUsageMiddleware, usage_of
from app.core.llm import settings

__all__ = [
    "llm_candidates", "chain", "model_chain",
    "structured",
    "TokenUsage", "TokenUsageMiddleware", "usage_of",
    "settings",
]
