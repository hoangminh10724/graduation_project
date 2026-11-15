"""Single-use account actions and durable email delivery queue."""
import sqlalchemy as sa
from alembic import op

revision = "0009_account_recovery"
down_revision = "0008_ai_requests"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email_verified", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.create_table(
        "account_actions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("purpose", sa.String(20), nullable=False),
        sa.Column("token_digest", sa.String(64), unique=True, nullable=False),
        sa.Column("token_version", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("consumed", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("delivery_status", sa.String(12), nullable=False),
        sa.Column("delivery_attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("available_at", sa.DateTime(), nullable=False),
        sa.Column("lease_token", sa.String(36), nullable=True),
        sa.Column("lease_until", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_account_actions_user_purpose", "account_actions", ["user_id", "purpose"])
    op.create_index("ix_account_actions_delivery", "account_actions", ["delivery_status", "available_at"])


def downgrade() -> None:
    op.drop_table("account_actions")
    with op.batch_alter_table("users") as batch:
        batch.drop_column("email_verified")
