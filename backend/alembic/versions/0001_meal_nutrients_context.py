"""add meal nutrient + health-context columns

Revision ID: 0001_meal_nutrients
Revises:
Create Date: 2026-07-03

"""
from alembic import op
import sqlalchemy as sa

revision = "0001_meal_nutrients"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("meal", sa.Column("sodium_mg", sa.Float(), nullable=False, server_default="0"))
    op.add_column("meal", sa.Column("fiber_g", sa.Float(), nullable=False, server_default="0"))
    op.add_column("meal", sa.Column("sugar_g", sa.Float(), nullable=False, server_default="0"))
    op.add_column("meal", sa.Column("ai_health_context", sa.Text(), nullable=True))
    op.add_column("meal", sa.Column("enriched_hash", sa.String(), nullable=True))
    op.add_column("meal", sa.Column("enriched_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("meal", "enriched_at")
    op.drop_column("meal", "enriched_hash")
    op.drop_column("meal", "ai_health_context")
    op.drop_column("meal", "sugar_g")
    op.drop_column("meal", "fiber_g")
    op.drop_column("meal", "sodium_mg")
