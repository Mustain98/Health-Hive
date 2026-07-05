"""widen unit columns to TEXT (LLM-generated units exceed varchar(20))

Revision ID: 0006_widen_unit
Revises: 0005_plan_setup_summary
Create Date: 2026-07-04

"""
from alembic import op
import sqlalchemy as sa

revision = "0006_widen_unit"
down_revision = "0005_plan_setup_summary"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("daily_goals", "unit", type_=sa.Text(), existing_type=sa.String(length=20), existing_nullable=True)
    op.alter_column("user_goals", "unit", type_=sa.Text(), existing_type=sa.String(length=20), existing_nullable=True)


def downgrade() -> None:
    op.alter_column("daily_goals", "unit", type_=sa.String(length=20), existing_type=sa.Text(), existing_nullable=True)
    op.alter_column("user_goals", "unit", type_=sa.String(length=20), existing_type=sa.Text(), existing_nullable=True)
