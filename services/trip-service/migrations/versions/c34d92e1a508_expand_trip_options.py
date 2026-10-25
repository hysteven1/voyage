"""Add optional origin and expanded trip preferences without changing existing plans."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "c34d92e1a508"
down_revision = "07fe4e0501c4"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("trips", "origin", existing_type=sa.String(255), nullable=True)
    op.add_column("trips", sa.Column("options", postgresql.JSONB(), nullable=True))
    op.add_column("trips", sa.Column("planning_error", sa.String(1000), nullable=True))


def downgrade():
    # Keep optional-origin trips representable when reverting to the old contract.
    op.execute(
        "UPDATE trips SET origin = 'Already at destination' WHERE origin IS NULL"
    )
    op.drop_column("trips", "planning_error")
    op.drop_column("trips", "options")
    op.alter_column("trips", "origin", existing_type=sa.String(255), nullable=False)
