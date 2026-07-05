"""introduce Plan (groups milestone + daily goals + nutrition target + meal setting)

Creates the `plans` table, adds `plan_id` to the four part tables, enforces one
active plan per user, and backfills each user's current ACTIVE parts into a plan.

Revision ID: 0007_plans
Revises: 0006_widen_unit
Create Date: 2026-07-04

"""
import uuid
from alembic import op
import sqlalchemy as sa

revision = "0007_plans"
down_revision = "0006_widen_unit"
branch_labels = None
depends_on = None

_PART_TABLES = ["user_goals", "nutrition_targets", "meal_plan_setting", "daily_goals"]


def upgrade() -> None:
    op.create_table(
        "plans",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_for", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False, server_default="My Plan"),
        sa.Column("source", sa.String(), nullable=False, server_default="self"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_plans_created_for", "plans", ["created_for"])
    op.execute("CREATE UNIQUE INDEX uq_plans_one_active ON plans (created_for) WHERE active")

    for t in _PART_TABLES:
        op.add_column(t, sa.Column("plan_id", sa.Uuid(), nullable=True))
        op.create_index(f"ix_{t}_plan_id", t, ["plan_id"])

    # Backfill: wrap each user's current ACTIVE parts into one active plan.
    conn = op.get_bind()
    users = conn.execute(sa.text(
        "SELECT DISTINCT created_for FROM user_goals WHERE active = true AND created_for IS NOT NULL "
        "UNION SELECT DISTINCT created_for FROM nutrition_targets WHERE active = true "
        "UNION SELECT DISTINCT created_for FROM meal_plan_setting WHERE active = true"
    )).fetchall()
    for (uid,) in users:
        pid = str(uuid.uuid4())
        conn.execute(sa.text(
            "INSERT INTO plans (id, created_for, created_by, name, source, active, created_at, updated_at) "
            "VALUES (:id, :u, :u, 'My Plan', 'self', true, now(), now())"), {"id": pid, "u": str(uid)})
        for t in _PART_TABLES:
            conn.execute(sa.text(f"UPDATE {t} SET plan_id = :pid WHERE created_for = :u AND active = true"),
                         {"pid": pid, "u": str(uid)})


def downgrade() -> None:
    for t in _PART_TABLES:
        op.drop_index(f"ix_{t}_plan_id", table_name=t)
        op.drop_column(t, "plan_id")
    op.execute("DROP INDEX IF EXISTS uq_plans_one_active")
    op.drop_table("plans")
