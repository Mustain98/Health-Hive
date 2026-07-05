"""add draft_plan_id to plan_setup_sessions (chat builds one draft Plan)

Revision ID: 0008_setup_draft_plan
Revises: 0007_plans
Create Date: 2026-07-04

"""
from alembic import op
import sqlalchemy as sa

revision = "0008_setup_draft_plan"
down_revision = "0007_plans"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("plan_setup_sessions", sa.Column("draft_plan_id", sa.Uuid(), nullable=True))


def downgrade() -> None:
    op.drop_column("plan_setup_sessions", "draft_plan_id")
