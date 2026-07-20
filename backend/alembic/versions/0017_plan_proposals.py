"""staged plan proposals replace the LangGraph approval interrupt

Adds `plan_proposals` and `plan_setup_sessions.pending_proposal_id`; drops
`pending_thread_id`.

Approval used to be a middleware `interrupt()` that suspended the agent graph. That had
three consequences visible to users: the model never got to speak before suspending, so
the reply fell back to "Sorry, could you rephrase that?"; each assistant message raised
its own interrupt, so nine habits became nine separate approval cards; and the decision
summary was written before the resumed tool ran, so the transcript claimed "Approved and
saved" for writes the risk guard then refused.

Proposals are staged rows instead. The card is built from a whole batch, approved items
are applied by server code, and what is reported is what actually happened.

`pending_thread_id` is dropped rather than migrated: it pointed at a suspended graph
thread, a concept that no longer exists. Any approval in flight at deploy time is lost —
nothing was written, so the user simply asks again.

Revision ID: 0017_plan_proposals
Revises: 0016_pending_thread
Create Date: 2026-07-20
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0017_plan_proposals"
down_revision = "0016_pending_thread"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "plan_proposals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("plan_setup_sessions.id"), nullable=False, index=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("items", sa.JSON(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index("ix_plan_proposals_created_at", "plan_proposals", ["created_at"])

    op.add_column(
        "plan_setup_sessions",
        sa.Column("pending_proposal_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_plan_setup_sessions_pending_proposal_id",
                    "plan_setup_sessions", ["pending_proposal_id"])
    op.drop_column("plan_setup_sessions", "pending_thread_id")


def downgrade() -> None:
    op.add_column(
        "plan_setup_sessions",
        sa.Column("pending_thread_id", sa.String(length=64), nullable=True),
    )
    op.drop_index("ix_plan_setup_sessions_pending_proposal_id", "plan_setup_sessions")
    op.drop_column("plan_setup_sessions", "pending_proposal_id")
    op.drop_index("ix_plan_proposals_created_at", "plan_proposals")
    op.drop_table("plan_proposals")
