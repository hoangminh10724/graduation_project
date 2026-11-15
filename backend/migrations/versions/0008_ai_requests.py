"""Durable request identities and committed results for audio and Talk."""
import sqlalchemy as sa
from alembic import op

revision = "0008_ai_requests"
down_revision = "0007_attempt_history"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("request_id", sa.String(36), nullable=False),
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("events_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("deadline", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "request_id", name="uq_ai_requests_user_request"),
    )


def downgrade() -> None:
    op.drop_table("ai_requests")
