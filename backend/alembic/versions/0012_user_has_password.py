"""add has_password to users

Distinguishes accounts that hold a real password from Google-created accounts that
hold only a random unusable hash, so the profile page can show "set" vs "change"
password. Every existing user registered with a password, so they backfill to true.

Revision ID: 0012_user_has_password
Revises: 0011_meal_plan_dow
Create Date: 2026-07-15

"""
from alembic import op
import sqlalchemy as sa

revision = "0012_user_has_password"
down_revision = "0011_meal_plan_dow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("has_password", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    # Existing rows all registered with a password; the server_default already set them
    # to true. Drop the server default so the app model (default=True) is the source of
    # truth and Google inserts can pass has_password=False explicitly.
    op.alter_column("users", "has_password", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "has_password")
