"""Add learner preferences and revocable login sessions."""
import sqlalchemy as sa
from alembic import op

revision = "0006_accounts"
down_revision = "0005_card_management"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for column in (
        sa.Column("display_name", sa.String(120), server_default="", nullable=False),
        sa.Column("timezone_name", sa.String(80), server_default="Asia/Ho_Chi_Minh", nullable=False),
        sa.Column("cefr_level", sa.String(2), server_default="A2", nullable=False),
        sa.Column("daily_goal", sa.Integer(), server_default="10", nullable=False),
        sa.Column("token_version", sa.Integer(), server_default="0", nullable=False),
    ):
        op.add_column("users", column)
    op.create_table(
        "login_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("refresh_digest", sa.String(64), unique=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.create_index("ix_login_sessions_user_id", "login_sessions", ["user_id"])
    op.create_table(
        "used_refresh_tokens",
        sa.Column("digest", sa.String(64), primary_key=True),
        sa.Column("session_id", sa.String(36), sa.ForeignKey("login_sessions.id"), nullable=False),
    )
    op.create_index("ix_used_refresh_tokens_session_id", "used_refresh_tokens", ["session_id"])


def downgrade() -> None:
    op.drop_table("used_refresh_tokens")
    op.drop_table("login_sessions")
    with op.batch_alter_table("users") as batch:
        for name in ("token_version", "daily_goal", "cefr_level", "timezone_name", "display_name"):
            batch.drop_column(name)
