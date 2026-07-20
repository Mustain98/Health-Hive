"""Which specialist handles this turn.

Keyword matching, not an LLM call — routing runs on every turn, and a model call here
would add latency and cost to the path before the agent has even started. Order matters:
the checks run most-specific first, and anything ambiguous or multi-part falls through to
`coach`, which holds every tool. Mis-routing is therefore never fatal — the coach can
always do the work; a narrower specialist just does it with a smaller prompt.
"""


def route_turn(message: str) -> str:
    """The specialist name for this turn — a key of `specialists.SPECIALISTS`."""
    msg = message.lower()

    if any(k in msg for k in ["weight", "bmi", "gain", "lose", "milestone"]):
        return "milestone"
    if any(k in msg for k in ["habit", "exercise", "steps", "sleep", "daily goal", "workout"]):
        return "daily_goals"
    if any(k in msg for k in ["calories", "protein", "carbs", "fat", "macro", "nutrition"]):
        return "nutrition"
    if any(k in msg for k in ["breakfast", "lunch", "dinner", "snack", "meal"]):
        return "meals"

    # Ambiguous, multi-part, or a plain conversational turn.
    return "coach"
