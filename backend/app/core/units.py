"""Closed unit vocabulary, and the column type that enforces it.

Closing a unit vocabulary is what stops the LLM writing `"sets of 10-15 reps"` into a
unit column — a value long enough that Alembic 0006 had to widen `daily_goals.unit` to
TEXT. A closed enum turns that into a parse error at the structured-output boundary
instead of a stored row.

`sa_enum()` is the shared column type: `sa.Enum(..., native_enum=False,
values_callable=...)`, which renders as VARCHAR + CHECK. That stores the enum *value*
and avoids Postgres type juggling — the same pattern `plan/models.py` uses for
`PlanSource`.

Scope note: the modules that own a unit define their own enum (`DailyGoalUnit`,
`MilestoneUnit`) and pass it to `sa_enum()`. What lives here is `MeasureUnit` (shared by
`meal/` and `adminbackend`) plus `WeightUnit`/`DurationUnit`, held for the Phase-2
rollout described in `core/enums.py`. The other five (count/energy/mass/volume/serving)
were never adopted anywhere and have been removed.
"""
from enum import Enum


class WeightUnit(str, Enum):
    kg = "kg"
    lb = "lb"


class DurationUnit(str, Enum):
    min = "min"
    hr = "hr"


# ── Food measurement ───────────────────────────────────────────────────────

class MeasureUnit(str, Enum):
    """How a food item's nutrition is measured.

    ⚠️ DO NOT rename these members. SQLAlchemy persists the enum *name*, so the
    database holds "gram"/"milliliter" while the Python values are "g"/"ml", and
    `adminbackend` writes those names directly via Supabase REST. Renaming a member
    silently breaks both. (Values may be displayed; names are the storage contract.)
    """
    gram = "g"
    milliliter = "ml"
    piece = "piece"
    tbsp = "tbsp"


# Fixed width for every unit column. Without this SQLAlchemy sizes the VARCHAR to
# the longest current member (e.g. 8 for "portions"), so adding a longer member later
# would silently require a migration — and the model would disagree with 0013, which
# writes VARCHAR(20). Pinning it keeps metadata and migrations in step.
UNIT_COLUMN_LENGTH = 20


def sa_enum(enum_cls, *, name: str | None = None):
    """Column type for a closed unit enum: VARCHAR(20) + CHECK, storing the value."""
    from sqlalchemy import Enum as SAEnum
    longest = max(len(m.value) for m in enum_cls)
    if longest > UNIT_COLUMN_LENGTH:
        raise ValueError(
            f"{enum_cls.__name__} has a member longer than {UNIT_COLUMN_LENGTH} chars "
            f"({longest}); widen UNIT_COLUMN_LENGTH and add a migration."
        )
    return SAEnum(
        enum_cls,
        native_enum=False,
        # SQLAlchemy 1.4+ defaults create_constraint to False, which would leave a
        # freshly-created database with no CHECK while a migrated one has it.
        create_constraint=True,
        length=UNIT_COLUMN_LENGTH,
        name=name or f"ck_{enum_cls.__name__.lower()}",
        values_callable=lambda e: [m.value for m in e],
    )
