"""Store completed Talk turns."""

import sqlalchemy as sa
from alembic import op

revision = "0002_dialogue_turns"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dialogue_turns",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("sessions.id"), nullable=False),
        sa.Column("learner_text", sa.Text(), nullable=False),
        sa.Column("tutor_text", sa.Text(), nullable=False),
    )
    op.create_index("ix_dialogue_turns_session_id", "dialogue_turns", ["session_id"])


def downgrade() -> None:
    op.drop_table("dialogue_turns")
