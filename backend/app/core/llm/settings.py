"""LLM configuration, read from the environment.

Model names used to be hardcoded constants inside the agent module. They live here so
they can be changed per-deployment without a code edit, and so there is one place to
look when asking "which model is this running?".
"""
import os


def _env(name: str, default: str) -> str:
    v = os.getenv(name)
    return v.strip() if v and v.strip() else default


# Primary model, and the one used when the primary is rate-limited or erroring.
GROQ_MODEL = _env("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_FALLBACK_MODEL = _env("GROQ_FALLBACK_MODEL", "openai/gpt-oss-120b")

# Default sampling temperature for structured-output calls.
DEFAULT_TEMPERATURE = float(_env("LLM_DEFAULT_TEMPERATURE", "0.2"))

# Jina embeddings.
EMBED_MODEL = _env("JINA_EMBED_MODEL", "jina-embeddings-v3")
JINA_URL = _env("JINA_URL", "https://api.jina.ai/v1/embeddings")
EMBED_BATCH_SIZE = int(_env("JINA_BATCH_SIZE", "64"))
EMBED_TIMEOUT_SECONDS = float(_env("JINA_TIMEOUT_SECONDS", "30"))


def groq_api_keys() -> tuple[str, ...]:
    """All configured Groq API keys, in priority order."""
    keys = [os.getenv("GROQ_API_KEY"), os.getenv("GROQ_API_KEY_2"), os.getenv("GROQ_API_KEY_3")]
    keys = [k for k in keys if k]
    if not keys:
        raise RuntimeError(
            "No Groq API key configured (GROQ_API_KEY / GROQ_API_KEY_2 / GROQ_API_KEY_3)"
        )
    return tuple(keys)
