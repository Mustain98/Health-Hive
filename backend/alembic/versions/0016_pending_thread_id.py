"""track the graph thread suspended on a pending approval

Additive: `plan_setup_sessions.pending_thread_id`. Set when a turn interrupts for
approval, cleared when the decisions resolve it; doubles as the "something is pending"
flag for the UI. Also enables per-turn checkpointer threads — previously the thread id
was the session id, so every approval-mode turn appended the full history to the same
graph thread and state ballooned turn over turn.

Revision ID: 0016_pending_thread
Revises: 0015_approval_mode
Create Date: 2026-07-20
"""
from alembic import op
import sqlalchemy as sa

revision = "0016_pending_thread"
down_revision = "0015_approval_mode"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "plan_setup_sessions",
        sa.Column("pending_thread_id", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("plan_setup_sessions", "pending_thread_id")
