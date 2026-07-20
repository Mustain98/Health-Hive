"""per-chat approval mode for the setup chatbot

Additive: one boolean on `plan_setup_sessions`. When true, the agent's write tools
pause for the user's approve/edit/reject decision (human-in-the-loop) instead of
writing directly. Replaces the global SETUP_CHAT_HITL env gate with a per-session
choice; the env var remains only as the default for newly created sessions.

Revision ID: 0015_approval_mode
Revises: 0014_token_usage
Create Date: 2026-07-20
"""
from alembic import op
import sqlalchemy as sa

revision = "0015_approval_mode"
down_revision = "0014_token_usage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "plan_setup_sessions",
        sa.Column("approval_mode", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("plan_setup_sessions", "approval_mode")
