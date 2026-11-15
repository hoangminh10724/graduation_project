"""Record actual completion times; leave historical turns undated."""
import sqlalchemy as sa
from alembic import op

revision = "0013_talk_completion_time"
down_revision = "0012_request_cancellation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("dialogue_turns", sa.Column("completed_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("dialogue_turns") as batch:
        batch.drop_column("completed_at")
