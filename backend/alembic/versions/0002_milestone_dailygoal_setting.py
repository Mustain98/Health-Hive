"""add milestone fields to user_goals + timed-meal description

New tables (daily_goals, daily_goal_logs, daily_logs) are created by the app's
create_all() on startup, consistent with the base schema. This migration only
adds columns to the pre-existing user_goals and meal_plan_setting_timed_meal
tables, which create_all() cannot do.

Revision ID: 0002_milestone_dailygoal
Revises: 0001_meal_nutrients
Create Date: 2026-07-03

"""
from alembic import op
import sqlalchemy as sa

revision = "0002_milestone_dailygoal"
down_revision = "0001_meal_nutrients"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # user_goals → milestone fields (additive, back-compat with goal_type/target_weight)
    op.add_column("user_goals", sa.Column("milestone_type", sa.String(), nullable=True))
    op.add_column("user_goals", sa.Column("name", sa.String(length=255), nullable=True))
    op.add_column("user_goals", sa.Column("target_value", sa.Float(), nullable=True))
    op.add_column("user_goals", sa.Column("unit", sa.String(length=20), nullable=True))
    op.add_column(
        "user_goals",
        sa.Column("attributes", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
    )

    # meal_plan_setting_timed_meal → free-text description (labels now optional)
    op.add_column("meal_plan_setting_timed_meal", sa.Column("description", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("meal_plan_setting_timed_meal", "description")
    op.drop_column("user_goals", "attributes")
    op.drop_column("user_goals", "unit")
    op.drop_column("user_goals", "target_value")
    op.drop_column("user_goals", "name")
    op.drop_column("user_goals", "milestone_type")
