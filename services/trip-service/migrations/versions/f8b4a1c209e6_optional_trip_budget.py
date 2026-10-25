"""Allow expanded trips to use a spending style without an amount."""

import sqlalchemy as sa
from alembic import op

revision = "f8b4a1c209e6"
down_revision = "c34d92e1a508"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("trips", "budget", existing_type=sa.Numeric(12, 2), nullable=True)


def downgrade():
    # PostgreSQL refuses this if budget-less trips remain; never invent amounts.
    op.alter_column("trips", "budget", existing_type=sa.Numeric(12, 2), nullable=False)
