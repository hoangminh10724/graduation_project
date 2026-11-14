"""Preserve pronunciation input provenance and Talk session links."""
import sqlalchemy as sa
from alembic import op

revision = "0007_attempt_history"
down_revision = "0006_accounts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("attempts") as batch:
        batch.add_column(sa.Column("reference_text", sa.Text(), nullable=True))
        batch.add_column(sa.Column("transcript", sa.Text(), nullable=True))
        batch.add_column(sa.Column("session_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_attempts_session_id", "sessions", ["session_id"], ["id"], ondelete="SET NULL")
        batch.create_index("ix_attempts_user_id_id", ["user_id", "id"])


def downgrade() -> None:
    with op.batch_alter_table("attempts") as batch:
        batch.drop_index("ix_attempts_user_id_id")
        batch.drop_constraint("fk_attempts_session_id", type_="foreignkey")
        for name in ("session_id", "transcript", "reference_text"):
            batch.drop_column(name)
