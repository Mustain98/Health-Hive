"""record LLM token usage per setup chat session

Purely additive: three counters on `plan_setup_sessions`, populated by
`TokenUsageMiddleware`. There is currently no data on what a setup chat actually costs,
so `MAX_MESSAGES` and the summarization trigger are guesses; these columns are the
measurement needed to replace them with real token budgets.

Revision ID: 0014_token_usage
Revises: 0013_close_units
Create Date: 2026-07-19
"""
from alembic import op
import sqlalchemy as sa

revision = "0014_token_usage"
down_revision = "0013_close_units"
branch_labels = None
depends_on = None


COLUMNS = ("total_input_tokens", "total_output_tokens", "llm_call_count")


def upgrade() -> None:
    for name in COLUMNS:
        op.add_column(
            "plan_setup_sessions",
            sa.Column(name, sa.Integer(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    for name in reversed(COLUMNS):
        op.drop_column("plan_setup_sessions", name)
