"""Prevent SQLite identity reuse after erasure; PostgreSQL already uses sequences."""
from alembic import op

revision = "0014_nonreusable_identities"
down_revision = "0013_talk_completion_time"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        for table in ("users", "sessions", "ai_requests"):
            with op.batch_alter_table(table, recreate="always", table_kwargs={"sqlite_autoincrement": True}):
                pass


def downgrade() -> None:
    # Keep the no-reuse property on downgrade too: older tokens/workers can
    # outlive an application rollback. No columns or API data need reverting.
    pass
