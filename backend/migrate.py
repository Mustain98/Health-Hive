"""
Migration script – safely adds new columns and tables for the follow-up feature.
Run from the backend/ directory:

    python migrate.py

This uses IF NOT EXISTS / ADD COLUMN IF NOT EXISTS so it is idempotent.
"""
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set in .env")

# psycopg2 needs postgresql:// not postgres://
url = DATABASE_URL.replace("postgresql://", "postgresql://", 1)

print(f"Connecting to DB...")
conn = psycopg2.connect(url)
conn.autocommit = True
cur = conn.cursor()

statements = [
    # ── Create followup_rooms table if it doesn't exist ──────────────────────
    """
    CREATE TABLE IF NOT EXISTS followup_rooms (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES users(id),
        consultant_user_id UUID NOT NULL REFERENCES users(id),
        status VARCHAR NOT NULL DEFAULT 'active',
        last_message_at TIMESTAMPTZ,
        created_from_appointment_id UUID,
        cancelled_by_user_id UUID REFERENCES users(id),
        cancelled_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,

    # ── Add created_from_appointment_id FK (after table exists) ──────────────
    # We skip adding it as a real FK initially (to avoid chicken-and-egg with appointments)
    # and just ensure the column exists

    # ── followup_messages ────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS followup_messages (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        room_id UUID NOT NULL REFERENCES followup_rooms(id),
        sender_user_id UUID NOT NULL REFERENCES users(id),
        message TEXT NOT NULL,
        is_system BOOLEAN NOT NULL DEFAULT FALSE,
        sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,

    # ── time_proposals ───────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS time_proposals (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        room_id UUID NOT NULL REFERENCES followup_rooms(id),
        proposed_by_user_id UUID NOT NULL REFERENCES users(id),
        start_at TIMESTAMPTZ NOT NULL,
        end_at TIMESTAMPTZ NOT NULL,
        status VARCHAR NOT NULL DEFAULT 'pending',
        appointment_id UUID,
        responded_by_user_id UUID REFERENCES users(id),
        responded_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,

    # ── Add followup_room_id to appointments (the critical missing column) ───
    """
    ALTER TABLE appointments
    ADD COLUMN IF NOT EXISTS followup_room_id UUID REFERENCES followup_rooms(id)
    """,

    # ── Add appointment_id FK on time_proposals (after appointments exists) ──
    """
    ALTER TABLE time_proposals
    ADD COLUMN IF NOT EXISTS appointment_id UUID REFERENCES appointments(id)
    """,

    # ── followup_rooms: add created_from_appointment_id FK ───────────────────
    """
    ALTER TABLE followup_rooms
    ADD COLUMN IF NOT EXISTS created_from_appointment_id UUID REFERENCES appointments(id)
    """,


    # ── Indexes ───────────────────────────────────────────────────────────────
    "CREATE INDEX IF NOT EXISTS ix_followup_rooms_user_id ON followup_rooms(user_id)",
    "CREATE INDEX IF NOT EXISTS ix_followup_rooms_consultant_user_id ON followup_rooms(consultant_user_id)",
    "CREATE INDEX IF NOT EXISTS ix_followup_rooms_status ON followup_rooms(status)",
    "CREATE INDEX IF NOT EXISTS ix_followup_messages_room_id ON followup_messages(room_id)",
    "CREATE INDEX IF NOT EXISTS ix_time_proposals_room_id ON time_proposals(room_id)",
    "CREATE INDEX IF NOT EXISTS ix_appointments_followup_room_id ON appointments(followup_room_id)",

    # ── followup_rooms: cancellation + reactivation columns ──────────────────
    "ALTER TABLE followup_rooms ADD COLUMN IF NOT EXISTS cancelled_by_user_id UUID REFERENCES users(id)",
    "ALTER TABLE followup_rooms ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMPTZ",
    "ALTER TABLE followup_rooms ADD COLUMN IF NOT EXISTS reactivated_at TIMESTAMPTZ",
]

for sql in statements:
    sql = sql.strip()
    if not sql:
        continue
    try:
        cur.execute(sql)
        print(f"  ✓  {sql[:70].replace(chr(10), ' ')}...")
    except Exception as e:
        print(f"  ✗  {sql[:70].replace(chr(10), ' ')}... ERROR: {e}")

cur.close()
conn.close()
print("\nMigration complete.")
