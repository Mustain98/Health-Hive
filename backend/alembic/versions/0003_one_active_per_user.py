"""enforce one active row per user (milestone / nutrition target / meal-plan setting)

Activation invariant: a user has at most ONE active UserGoal, NutritionTarget and
MealPlanSetting at a time. Previously only enforced in service code; this makes it a
DB guarantee (partial unique index), so the Phase-4 generation gate can trust the
"active" query. Existing duplicates are deactivated first (keeping the most recent).

Revision ID: 0003_one_active_per_user
Revises: 0002_milestone_dailygoal
Create Date: 2026-07-03

"""
from alembic import op

revision = "0003_one_active_per_user"
down_revision = "0002_milestone_dailygoal"
branch_labels = None
depends_on = None

# (table, owner column)
_TABLES = [
    ("user_goals", "created_for"),
    ("nutrition_targets", "created_for"),
    ("meal_plan_setting", "created_for"),
]


def upgrade() -> None:
    for table, owner in _TABLES:
        # 1) Deactivate all but the most-recent active row per owner.
        op.execute(f"""
            UPDATE {table} SET active = false
            WHERE active = true AND id NOT IN (
                SELECT DISTINCT ON ({owner}) id FROM {table}
                WHERE active = true
                ORDER BY {owner}, created_at DESC
            )
        """)
        # 2) Guarantee it going forward (partial unique index over active rows).
        op.execute(
            f"CREATE UNIQUE INDEX uq_{table}_one_active "
            f"ON {table} ({owner}) WHERE active"
        )


def downgrade() -> None:
    for table, _ in _TABLES:
        op.execute(f"DROP INDEX IF EXISTS uq_{table}_one_active")
