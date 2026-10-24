"""Add an optional display name; existing accounts retain a null name."""

import sqlalchemy as sa
from alembic import op

revision = "0003_user_name"
down_revision = "0002_create_vehicles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("name", sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "name")
