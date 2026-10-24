"""Add vehicle inventory without altering existing users."""

import sqlalchemy as sa
from alembic import op

revision = "0002_create_vehicles"
down_revision = "0001_create_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vehicles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("make", sa.String(100), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "price > 0 AND price <= 9999999999.99", name="ck_vehicles_price_positive"
        ),
        sa.CheckConstraint("quantity >= 0", name="ck_vehicles_quantity_nonnegative"),
        sa.CheckConstraint("length(btrim(make)) > 0", name="ck_vehicles_make_not_blank"),
        sa.CheckConstraint("length(btrim(model)) > 0", name="ck_vehicles_model_not_blank"),
        sa.CheckConstraint("length(btrim(category)) > 0", name="ck_vehicles_category_not_blank"),
    )


def downgrade() -> None:
    op.drop_table("vehicles")
