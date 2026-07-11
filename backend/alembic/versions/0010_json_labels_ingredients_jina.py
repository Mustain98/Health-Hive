"""compress meal/food_item into single tables + Jina embeddings

- Adds JSONB `labels` to food_item and meal, JSONB `ingredients` to meal.
- Backfills them from the label/link/ingredient tables (with parity checks),
  then drops food_item_label_link, meal_label_link, meal_food_item,
  food_item_label, meal_label and their orphaned enum types.
- Wipes meal_embedding (model change: fastembed 384-dim -> jina-embeddings-v3
  1024-dim) and widens the vector column.

Revision ID: 0010_json_labels_jina
Revises: 0009_dg_days_of_week
Create Date: 2026-07-11

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0010_json_labels_jina"
down_revision = "0009_dg_days_of_week"
branch_labels = None
depends_on = None


def _jsonb_col(name: str) -> sa.Column:
    return sa.Column(
        name,
        postgresql.JSONB(),
        nullable=False,
        server_default=sa.text("'[]'::jsonb"),
    )


def _check(conn, description: str, left_sql: str, right_sql: str) -> None:
    left = conn.execute(sa.text(left_sql)).scalar() or 0
    right = conn.execute(sa.text(right_sql)).scalar() or 0
    if left != right:
        raise RuntimeError(
            f"Backfill parity check failed for {description}: {left} link rows vs {right} JSON entries. "
            "Aborting before any table is dropped."
        )


def upgrade() -> None:
    conn = op.get_bind()

    # 1. New JSONB columns
    op.add_column("food_item", _jsonb_col("labels"))
    op.add_column("meal", _jsonb_col("labels"))
    op.add_column("meal", _jsonb_col("ingredients"))

    # 2. Backfill from the link tables (enum columns cast to text)
    op.execute("""
        UPDATE food_item f SET labels = sub.lbls
        FROM (SELECT lnk.food_item_id, jsonb_agg(DISTINCT lbl.name::text) AS lbls
              FROM food_item_label_link lnk
              JOIN food_item_label lbl ON lbl.id = lnk.food_item_label_id
              GROUP BY lnk.food_item_id) sub
        WHERE f.id = sub.food_item_id
    """)
    op.execute("""
        UPDATE meal m SET labels = sub.lbls
        FROM (SELECT lnk.meal_id, jsonb_agg(DISTINCT lbl.name::text) AS lbls
              FROM meal_label_link lnk
              JOIN meal_label lbl ON lbl.id = lnk.meal_label_id
              GROUP BY lnk.meal_id) sub
        WHERE m.id = sub.meal_id
    """)
    op.execute("""
        UPDATE meal m SET ingredients = sub.ing
        FROM (SELECT mfi.meal_id,
                     jsonb_agg(jsonb_build_object(
                         'food_item_id', mfi.food_item_id::text,
                         'quantity', mfi.quantity,
                         'unit', mfi.unit::text
                     ) ORDER BY mfi.created_at) AS ing
              FROM meal_food_item mfi
              GROUP BY mfi.meal_id) sub
        WHERE m.id = sub.meal_id
    """)

    # 3. Parity checks — abort (whole migration rolls back) on any mismatch.
    #    (Verified beforehand: no duplicate link rows exist, so strict counts hold.)
    _check(
        conn, "food_item.labels",
        "SELECT count(*) FROM food_item_label_link",
        "SELECT coalesce(sum(jsonb_array_length(labels)), 0) FROM food_item",
    )
    _check(
        conn, "meal.labels",
        "SELECT count(*) FROM meal_label_link",
        "SELECT coalesce(sum(jsonb_array_length(labels)), 0) FROM meal",
    )
    _check(
        conn, "meal.ingredients",
        "SELECT count(*) FROM meal_food_item",
        "SELECT coalesce(sum(jsonb_array_length(ingredients)), 0) FROM meal",
    )

    # 4. Drop the link tables first, then the label tables
    op.drop_table("food_item_label_link")
    op.drop_table("meal_label_link")
    op.drop_table("meal_food_item")
    op.drop_table("food_item_label")
    op.drop_table("meal_label")

    # 5. Drop the now-orphaned enum types (names verified in pg_type)
    op.execute("DROP TYPE IF EXISTS fooditemlabelname")
    op.execute("DROP TYPE IF EXISTS meallabelname")

    # 6. Embeddings: model change -> wipe rows and widen the vector column.
    #    Rows regenerate lazily (hash+model gated) on the next plan generation.
    op.execute("DELETE FROM meal_embedding")
    op.execute("ALTER TABLE meal_embedding ALTER COLUMN embedding TYPE vector(1024)")


def downgrade() -> None:
    # Lossy-but-correct reverse: recreate tables/enums and re-expand the JSON columns.
    op.execute("ALTER TABLE meal_embedding ALTER COLUMN embedding TYPE vector(384)")
    op.execute("DELETE FROM meal_embedding")

    op.execute("""CREATE TYPE fooditemlabelname AS ENUM (
        'grain','meat','fish','dairy','vegetable','fruit','legume','nut_seed','oil_fat',
        'beverage','spice','sweetener','halal','vegetarian','vegan','egg','gluten','nuts',
        'shellfish','soy','high_protein','high_fiber','low_carb','low_fat','other')""")
    op.execute("""CREATE TYPE meallabelname AS ENUM (
        'breakfast','lunch','dinner','snack','main_meal','side_meal','drink','dessert',
        'halal','vegetarian','vegan','high_protein','low_carb','gym_friendly','other')""")

    op.create_table(
        "food_item_label",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", postgresql.ENUM(name="fooditemlabelname", create_type=False), nullable=False, unique=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_table(
        "meal_label",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", postgresql.ENUM(name="meallabelname", create_type=False), nullable=False, unique=True),
        sa.Column("description", sa.String(), nullable=True),
    )
    op.create_table(
        "food_item_label_link",
        sa.Column("food_item_id", sa.Uuid(), sa.ForeignKey("food_item.id"), primary_key=True),
        sa.Column("food_item_label_id", sa.Uuid(), sa.ForeignKey("food_item_label.id"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_table(
        "meal_label_link",
        sa.Column("meal_id", sa.Uuid(), sa.ForeignKey("meal.id"), primary_key=True),
        sa.Column("meal_label_id", sa.Uuid(), sa.ForeignKey("meal_label.id"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_table(
        "meal_food_item",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("meal_id", sa.Uuid(), sa.ForeignKey("meal.id"), nullable=False, index=True),
        sa.Column("food_item_id", sa.Uuid(), sa.ForeignKey("food_item.id"), nullable=False, index=True),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("unit", postgresql.ENUM(name="measureunit", create_type=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.execute("""
        INSERT INTO food_item_label (name)
        SELECT DISTINCT jsonb_array_elements_text(labels)::fooditemlabelname FROM food_item
    """)
    op.execute("""
        INSERT INTO meal_label (name)
        SELECT DISTINCT jsonb_array_elements_text(labels)::meallabelname FROM meal
    """)
    op.execute("""
        INSERT INTO food_item_label_link (food_item_id, food_item_label_id)
        SELECT f.id, lbl.id
        FROM food_item f, jsonb_array_elements_text(f.labels) AS l(name)
        JOIN food_item_label lbl ON lbl.name = l.name::fooditemlabelname
    """)
    op.execute("""
        INSERT INTO meal_label_link (meal_id, meal_label_id)
        SELECT m.id, lbl.id
        FROM meal m, jsonb_array_elements_text(m.labels) AS l(name)
        JOIN meal_label lbl ON lbl.name = l.name::meallabelname
    """)
    op.execute("""
        INSERT INTO meal_food_item (meal_id, food_item_id, quantity, unit)
        SELECT m.id, (ing->>'food_item_id')::uuid, (ing->>'quantity')::float, (ing->>'unit')::measureunit
        FROM meal m, jsonb_array_elements(m.ingredients) AS ing
        WHERE ing->>'food_item_id' IS NOT NULL
    """)

    op.drop_column("meal", "ingredients")
    op.drop_column("meal", "labels")
    op.drop_column("food_item", "labels")
