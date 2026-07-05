"""add rolling-memory summary column to plan_setup_sessions

Column add to an existing table (the table itself is created by create_all).

Revision ID: 0005_plan_setup_summary
Revises: 0004_notifications_table
Create Date: 2026-07-04

"""
from alembic import op
import sqlalchemy as sa

revision = "0005_plan_setup_summary"
down_revision = "0004_notifications_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("plan_setup_sessions", sa.Column("summary", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("plan_setup_sessions", "summary")
