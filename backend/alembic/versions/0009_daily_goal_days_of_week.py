"""add days_of_week to daily_goals (weekday schedule; Mon=0 … Sun=6, NULL = every day)

The daily_goals table was originally created by ``create_all`` before the
model gained ``days_of_week``, so existing databases lack the column.

Revision ID: 0009_dg_days_of_week
Revises: 0008_setup_draft_plan
Create Date: 2026-07-05

"""
from alembic import op
import sqlalchemy as sa

revision = "0009_dg_days_of_week"
down_revision = "0008_setup_draft_plan"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("daily_goals", sa.Column("days_of_week", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("daily_goals", "days_of_week")
