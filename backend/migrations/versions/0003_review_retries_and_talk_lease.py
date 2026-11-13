"""Persist review retry results and reserve active Talk turns."""
import sqlalchemy as sa
from alembic import op

revision = "0003_review_retries"
down_revision = "0002_dialogue_turns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sessions", sa.Column("busy_until", sa.DateTime(), nullable=True))
    op.add_column("sessions", sa.Column("turn_token", sa.String(36), nullable=True))
    with op.batch_alter_table("reviews") as batch:
        batch.add_column(sa.Column("request_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("result_json", sa.Text(), nullable=True))
        batch.create_unique_constraint("uq_reviews_request_id", ["request_id"])


def downgrade() -> None:
    with op.batch_alter_table("reviews") as batch:
        batch.drop_constraint("uq_reviews_request_id", type_="unique")
        batch.drop_column("result_json")
        batch.drop_column("request_id")
    op.drop_column("sessions", "turn_token")
    op.drop_column("sessions", "busy_until")
