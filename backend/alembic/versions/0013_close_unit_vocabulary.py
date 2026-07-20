"""close the unit vocabulary + type daily-goal attributes

Reverts 0006 ("widen unit columns to TEXT (LLM-generated units exceed varchar(20))").
Rather than widening the column to fit whatever the model emitted, the vocabulary is
closed and the existing values are mapped onto it.

Backfill is derived from an audit of the live data (see docs/REFACTOR_PLAN.md):

  daily_goals.unit   sets(10) minutes(4) kcal(2) reps(2) glasses(2) min(1) steps(1)
                     + "sets of 10-15 reps", "sets of 10-12 reps", "sets of 12-15 reps"
  user_goals.unit    NULL(20) kg(2)
  attributes keys    day(5) sets(4) reps(3) hold_time(1) per_leg(1)

Order is: preserve originals -> backfill -> migrate attribute keys -> narrow.
`unit_legacy` keeps every original string so nothing is destroyed; it is dropped in a
later migration once confirmed empty of anything unmapped.

Revision ID: 0013_close_units
Revises: 0012_user_has_password
Create Date: 2026-07-19
"""
from alembic import op
import sqlalchemy as sa

revision = "0013_close_units"
down_revision = "0012_user_has_password"
branch_labels = None
depends_on = None


DAILY_GOAL_UNITS = [
    "min", "hr", "reps", "sets", "steps", "times", "kcal",
    "g", "mg", "ml", "l", "glasses", "servings", "portions",
]
MILESTONE_UNITS = ["kg", "lb", "pct_body_fat"]

# Weekday name -> Mon=0 … Sun=6, matching normalize_days_of_week().
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# days_of_week is JSON and holds BOTH SQL NULL and JSON `null` in production.
# COALESCE only catches the former, so appending to a JSON `null` would yield
# [null, 1, 3] — which normalize_days_of_week() then silently reduces to "every
# day", i.e. the wrong schedule. Normalise both to an empty array first.
_DOW = ("CASE WHEN days_of_week IS NULL OR days_of_week::jsonb = 'null'::jsonb "
        "THEN '[]'::jsonb ELSE days_of_week::jsonb END")


def upgrade() -> None:
    conn = op.get_bind()

    # ── 1. Preserve every original unit string before touching anything ──────
    op.add_column("daily_goals", sa.Column("unit_legacy", sa.Text(), nullable=True))
    op.add_column("user_goals", sa.Column("unit_legacy", sa.Text(), nullable=True))
    conn.execute(sa.text("UPDATE daily_goals SET unit_legacy = unit WHERE unit IS NOT NULL"))
    conn.execute(sa.text("UPDATE user_goals  SET unit_legacy = unit WHERE unit IS NOT NULL"))

    # ── 2. Backfill daily_goals.unit onto the closed vocabulary ──────────────
    # Straight renames / case+whitespace normalisation.
    conn.execute(sa.text("""
        UPDATE daily_goals SET unit = CASE lower(btrim(unit))
            WHEN 'minutes' THEN 'min'
            WHEN 'mins'    THEN 'min'
            WHEN 'minute'  THEN 'min'
            WHEN 'hours'   THEN 'hr'
            WHEN 'hour'    THEN 'hr'
            WHEN 'rep'     THEN 'reps'
            WHEN 'set'     THEN 'sets'
            WHEN 'step'    THEN 'steps'
            WHEN 'glass'   THEN 'glasses'
            WHEN 'calories' THEN 'kcal'
            WHEN 'cal'      THEN 'kcal'
            ELSE lower(btrim(unit))
        END
        WHERE unit IS NOT NULL
    """))

    # The hallucinated "sets of N-M reps" values: unit becomes 'sets' and the rep
    # range is lifted into attributes, where it is actually queryable.
    conn.execute(sa.text(r"""
        UPDATE daily_goals
           SET attributes = (
                   attributes::jsonb || jsonb_build_object(
                       'reps_min', (regexp_match(unit, '(\d+)\s*-\s*(\d+)'))[1]::int,
                       'reps_max', (regexp_match(unit, '(\d+)\s*-\s*(\d+)'))[2]::int
                   )
               )::json,
               unit = 'sets'
         WHERE unit ~ 'sets? of \d+\s*-\s*\d+\s*reps?'
    """))

    # Anything still outside the vocabulary -> NULL (original kept in unit_legacy).
    conn.execute(sa.text(
        "UPDATE daily_goals SET unit = NULL WHERE unit IS NOT NULL AND unit <> ALL(:allowed)"
    ).bindparams(sa.bindparam("allowed", value=DAILY_GOAL_UNITS, type_=sa.ARRAY(sa.Text))))

    # ── 3. Backfill user_goals.unit ──────────────────────────────────────────
    conn.execute(sa.text("""
        UPDATE user_goals SET unit = CASE lower(btrim(unit))
            WHEN 'kgs'       THEN 'kg'
            WHEN 'kilogram'  THEN 'kg'
            WHEN 'kilograms' THEN 'kg'
            WHEN 'lbs'       THEN 'lb'
            WHEN 'pound'     THEN 'lb'
            WHEN 'pounds'    THEN 'lb'
            WHEN 'kg_muscle' THEN 'kg'
            ELSE lower(btrim(unit))
        END
        WHERE unit IS NOT NULL
    """))
    conn.execute(sa.text(
        "UPDATE user_goals SET unit = NULL WHERE unit IS NOT NULL AND unit <> ALL(:allowed)"
    ).bindparams(sa.bindparam("allowed", value=MILESTONE_UNITS, type_=sa.ARRAY(sa.Text))))

    # ── 4. Migrate attribute keys that extra="forbid" would now reject ───────
    # `day` holds weekday NAMES and duplicates the days_of_week column; every row
    # carrying it has days_of_week IS NULL, so there is nothing to conflict with.
    for idx, name in enumerate(WEEKDAYS):
        # NB: casts are spelled CAST(:p AS t), not :p::t — SQLAlchemy's text() bind
        # parser does not substitute a parameter followed immediately by `::`.
        conn.execute(sa.text(f"""
            UPDATE daily_goals
               SET days_of_week = ({_DOW} || to_jsonb(CAST(:idx AS int)))::json
             WHERE attributes::jsonb ? 'day'
               AND attributes::jsonb -> 'day' @> to_jsonb(CAST(:name AS text))
               AND NOT {_DOW} @> to_jsonb(CAST(:idx AS int))
        """).bindparams(idx=idx, name=name))
    conn.execute(sa.text(
        "UPDATE daily_goals SET attributes = (attributes::jsonb - 'day')::json "
        "WHERE attributes::jsonb ? 'day'"
    ))

    # `hold_time` (seconds) -> `hold_time_sec`, so the unit is in the name.
    conn.execute(sa.text("""
        UPDATE daily_goals
           SET attributes = ((attributes::jsonb - 'hold_time')
                 || jsonb_build_object('hold_time_sec', attributes::jsonb -> 'hold_time'))::json
         WHERE attributes::jsonb ? 'hold_time'
    """))

    # ── 5. Narrow the columns — this is the actual revert of 0006 ────────────
    op.alter_column("daily_goals", "unit", type_=sa.String(length=20),
                    existing_type=sa.Text(), existing_nullable=True)
    op.alter_column("user_goals", "unit", type_=sa.String(length=20),
                    existing_type=sa.Text(), existing_nullable=True)
    op.create_check_constraint(
        "ck_daily_goals_unit", "daily_goals",
        sa.column("unit").in_(DAILY_GOAL_UNITS) | sa.column("unit").is_(None),
    )
    op.create_check_constraint(
        "ck_user_goals_unit", "user_goals",
        sa.column("unit").in_(MILESTONE_UNITS) | sa.column("unit").is_(None),
    )


def downgrade() -> None:
    conn = op.get_bind()
    op.drop_constraint("ck_user_goals_unit", "user_goals", type_="check")
    op.drop_constraint("ck_daily_goals_unit", "daily_goals", type_="check")
    op.alter_column("user_goals", "unit", type_=sa.Text(),
                    existing_type=sa.String(length=20), existing_nullable=True)
    op.alter_column("daily_goals", "unit", type_=sa.Text(),
                    existing_type=sa.String(length=20), existing_nullable=True)

    # Restore the original strings from unit_legacy.
    conn.execute(sa.text("UPDATE daily_goals SET unit = unit_legacy WHERE unit_legacy IS NOT NULL"))
    conn.execute(sa.text("UPDATE user_goals  SET unit = unit_legacy WHERE unit_legacy IS NOT NULL"))

    conn.execute(sa.text("""
        UPDATE daily_goals
           SET attributes = ((attributes::jsonb - 'hold_time_sec')
                 || jsonb_build_object('hold_time', attributes::jsonb -> 'hold_time_sec'))::json
         WHERE attributes::jsonb ? 'hold_time_sec'
    """))
    conn.execute(sa.text(
        "UPDATE daily_goals SET attributes = (attributes::jsonb - 'reps_min' - 'reps_max')::json "
        "WHERE attributes::jsonb ?| array['reps_min','reps_max']"
    ))

    op.drop_column("user_goals", "unit_legacy")
    op.drop_column("daily_goals", "unit_legacy")
