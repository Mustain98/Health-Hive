from enum import Enum
from typing import Optional


def short(s, n: int = 40) -> Optional[str]:
    """Trim a (possibly LLM-generated) short label to a sane length.

    Enum-aware on purpose. `str()` on a `(str, Enum)` member returns
    ``"DailyGoalUnit.glasses"`` in Python 3.11+, not ``"glasses"`` — so passing an
    enum through here wrote the *repr* into the column. That surfaced as

        value too long for type character varying(20)

    on `daily_goals.unit` once units became enums. Unwrapping the value here makes
    every existing and future call site safe, rather than relying on each one
    remembering not to wrap an enum.
    """
    if s is None:
        return None
    if isinstance(s, Enum):
        s = s.value
    s = str(s).strip()
    return s[:n] if len(s) > n else s
