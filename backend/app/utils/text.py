from typing import Optional


def short(s: Optional[str], n: int = 40) -> Optional[str]:
    """Trim a (possibly LLM-generated) short label to a sane length. Keeps units/names tidy."""
    if s is None:
        return None
    s = str(s).strip()
    return s[:n] if len(s) > n else s
