"""Persistent study queues and per-session review outcomes."""
import sqlalchemy as sa
from alembic import op

revision = "0011_study_sessions"
down_revision = "0010_talk_management"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "study_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("request_id", sa.String(36), nullable=False),
        sa.Column("selection_json", sa.Text(), nullable=False),
        sa.Column("deck_id", sa.Integer(), sa.ForeignKey("decks.id", ondelete="SET NULL")),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime()),
        sa.UniqueConstraint("user_id", "request_id", name="uq_study_user_request"),
    )
    op.create_index("ix_study_user_id", "study_sessions", ["user_id", "id"])
    op.create_index("uq_study_active_user", "study_sessions", ["user_id"], unique=True,
                    postgresql_where=sa.text("status = 'active'"), sqlite_where=sa.text("status = 'active'"))
    op.create_table(
        "study_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("study_session_id", sa.Integer(), sa.ForeignKey("study_sessions.id"), nullable=False),
        sa.Column("card_id", sa.Integer(), sa.ForeignKey("cards.id", ondelete="SET NULL")),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("expected_due", sa.DateTime(), nullable=False),
        sa.Column("state", sa.String(12), nullable=False),
        sa.Column("skip_reason", sa.String(30)),
        sa.Column("rating", sa.Integer()),
        sa.Column("reviewed_at", sa.DateTime()),
        sa.UniqueConstraint("study_session_id", "card_id", name="uq_study_item_card"),
    )
    op.create_index("ix_study_items_card_id", "study_items", ["card_id"])
    with op.batch_alter_table("reviews") as batch:
        batch.add_column(sa.Column("study_session_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_reviews_study_session", "study_sessions", ["study_session_id"], ["id"])
        batch.create_index("ix_reviews_study_session_id", ["study_session_id"])


def downgrade() -> None:
    with op.batch_alter_table("reviews") as batch:
        batch.drop_index("ix_reviews_study_session_id")
        batch.drop_constraint("fk_reviews_study_session", type_="foreignkey")
        batch.drop_column("study_session_id")
    op.drop_table("study_items")
    op.drop_table("study_sessions")
