"""Associate AI requests with the exact Talk reservation they may release."""
import sqlalchemy as sa
from alembic import op

revision = "0012_request_cancellation"
down_revision = "0011_study_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ai_requests", sa.Column("turn_token", sa.String(36), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("ai_requests") as batch:
        batch.drop_column("turn_token")
