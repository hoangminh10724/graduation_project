"""Add decks and suspension without resetting existing review schedules."""
import sqlalchemy as sa
from alembic import op

revision = "0005_card_management"
down_revision = "0004_rate_limits"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "decks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.String(1000), nullable=False),
    )
    op.create_index("ix_decks_user_id", "decks", ["user_id"])
    with op.batch_alter_table("cards") as batch:
        batch.add_column(sa.Column("deck_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("suspended", sa.Boolean(), server_default=sa.false(), nullable=False))
        batch.create_foreign_key("fk_cards_deck_id", "decks", ["deck_id"], ["id"], ondelete="SET NULL")
        batch.create_index("ix_cards_user_due", ["user_id", "suspended", "due", "id"])
    op.create_index("ix_reviews_card_time", "reviews", ["card_id", "reviewed_at"])


def downgrade() -> None:
    op.drop_index("ix_reviews_card_time", table_name="reviews")
    with op.batch_alter_table("cards") as batch:
        batch.drop_index("ix_cards_user_due")
        batch.drop_constraint("fk_cards_deck_id", type_="foreignkey")
        batch.drop_column("suspended")
        batch.drop_column("deck_id")
    op.drop_table("decks")
