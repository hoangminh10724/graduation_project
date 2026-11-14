"""Add shared request budgets."""
import sqlalchemy as sa
from alembic import op

revision = "0004_rate_limits"
down_revision = "0003_review_retries"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rate_limits",
        sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("window_start", sa.DateTime(), nullable=False),
        sa.Column("hits", sa.Integer(), nullable=False),
    )
    op.create_index("ix_rate_limits_window_start", "rate_limits", ["window_start"])


def downgrade() -> None:
    op.drop_table("rate_limits")
