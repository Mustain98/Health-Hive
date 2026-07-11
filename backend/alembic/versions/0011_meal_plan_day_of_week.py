"""drop dates from meal plans; key day plans on weekday instead

Meal plans were date-aware (week_meal_plan.start_date/end_date, day_meal_plan.plan_date)
even though the product only ever wanted weekday awareness — the UI picked a weekday and
converted it to "the next occurring date" just to satisfy the API.

A user now has exactly one WeekMealPlan: a recurring Mon-Sun template holding up to seven
DayMealPlans keyed on day_of_week (Mon=0 … Sun=6, same convention as daily_goals.days_of_week).

Backfills day_of_week from plan_date, collapses each user's week plans into one, drops the
duplicate (user, weekday) day plans that fall out of that collapse (keeping the newest), then
drops the date columns and enforces the new uniqueness.

Revision ID: 0011_meal_plan_dow
Revises: 0010_json_labels_jina
Create Date: 2026-07-12

"""
from alembic import op
import sqlalchemy as sa

revision = "0011_meal_plan_dow"
down_revision = "0010_json_labels_jina"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. weekday column, backfilled from the date (ISODOW is Mon=1 … Sun=7).
    op.add_column("day_meal_plan", sa.Column("day_of_week", sa.Integer(), nullable=True))
    op.execute("UPDATE day_meal_plan SET day_of_week = EXTRACT(ISODOW FROM plan_date)::int - 1")

    # 2. One keeper week plan per user (the most recent). Week plans with no user_id are
    #    orphans from the old degenerate "1-day week" path and can't be attributed — drop them.
    op.execute(
        """
        CREATE TEMP TABLE keeper_week AS
        SELECT DISTINCT ON (user_id) user_id, id
        FROM week_meal_plan
        WHERE user_id IS NOT NULL
        ORDER BY user_id, created_at DESC
        """
    )

    # 3. Of each user's day plans, keep the newest per weekday; the rest are duplicates
    #    (the same weekday planned in several calendar weeks).
    op.execute(
        """
        CREATE TEMP TABLE doomed_day AS
        SELECT d.id
        FROM (
            SELECT d.id,
                   ROW_NUMBER() OVER (
                       PARTITION BY w.user_id, d.day_of_week
                       ORDER BY d.created_at DESC
                   ) AS rn
            FROM day_meal_plan d
            JOIN week_meal_plan w ON w.id = d.week_plan_id
            WHERE w.user_id IS NOT NULL
        ) d
        WHERE d.rn > 1
        UNION
        -- day plans hanging off an unattributable week plan
        SELECT d.id
        FROM day_meal_plan d
        JOIN week_meal_plan w ON w.id = d.week_plan_id
        WHERE w.user_id IS NULL
        """
    )

    # 4. Delete doomed day plans bottom-up (no ON DELETE CASCADE on these FKs).
    op.execute(
        """
        DELETE FROM timed_meal_combo_option
        WHERE timed_meal_id IN (
            SELECT id FROM timed_meal WHERE day_plan_id IN (SELECT id FROM doomed_day)
        )
        """
    )
    op.execute("DELETE FROM timed_meal WHERE day_plan_id IN (SELECT id FROM doomed_day)")
    op.execute("DELETE FROM day_meal_plan WHERE id IN (SELECT id FROM doomed_day)")

    # 5. Repoint the survivors onto their user's keeper week plan, then drop the rest.
    op.execute(
        """
        UPDATE day_meal_plan d
        SET week_plan_id = k.id
        FROM week_meal_plan w
        JOIN keeper_week k ON k.user_id = w.user_id
        WHERE w.id = d.week_plan_id AND d.week_plan_id <> k.id
        """
    )
    op.execute("DELETE FROM week_meal_plan WHERE id NOT IN (SELECT id FROM keeper_week)")

    # 6. Drop the dates.
    op.alter_column("day_meal_plan", "day_of_week", nullable=False)
    op.drop_column("day_meal_plan", "plan_date")
    op.drop_column("week_meal_plan", "start_date")
    op.drop_column("week_meal_plan", "end_date")

    # 7. Enforce: one week plan per user, one day plan per weekday within it.
    op.create_index("ix_day_meal_plan_day_of_week", "day_meal_plan", ["day_of_week"])
    op.create_unique_constraint(
        "uq_day_meal_plan_week_dow", "day_meal_plan", ["week_plan_id", "day_of_week"]
    )
    op.create_unique_constraint("uq_week_meal_plan_user", "week_meal_plan", ["user_id"])


def downgrade() -> None:
    # The calendar dates are gone for good; restore the columns as nullable so the schema
    # round-trips, but the original plan_date values are not recoverable.
    op.drop_constraint("uq_week_meal_plan_user", "week_meal_plan", type_="unique")
    op.drop_constraint("uq_day_meal_plan_week_dow", "day_meal_plan", type_="unique")
    op.drop_index("ix_day_meal_plan_day_of_week", table_name="day_meal_plan")

    op.add_column("week_meal_plan", sa.Column("end_date", sa.Date(), nullable=True))
    op.add_column("week_meal_plan", sa.Column("start_date", sa.Date(), nullable=True))
    op.add_column("day_meal_plan", sa.Column("plan_date", sa.Date(), nullable=True))
    op.drop_column("day_meal_plan", "day_of_week")
