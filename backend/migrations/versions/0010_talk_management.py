"""Talk titles, pagination index and links to replay results."""
import json

import sqlalchemy as sa
from alembic import op

revision = "0010_talk_management"
down_revision = "0009_account_recovery"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sessions", sa.Column("title", sa.String(120), server_default="", nullable=False))
    op.create_index("ix_sessions_user_id_id", "sessions", ["user_id", "id"])
    with op.batch_alter_table("ai_requests") as batch:
        batch.add_column(sa.Column("session_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_ai_requests_session_id", "sessions", ["session_id"], ["id"], ondelete="SET NULL")
        batch.create_index("ix_ai_requests_session_id", ["session_id"])
    connection = op.get_bind()
    connection.execute(sa.text("UPDATE sessions SET title=CASE WHEN topic='' THEN 'New conversation' ELSE topic END"))
    # Legacy requests did not record their session directly. Resolve only from committed results.
    rows = connection.execute(sa.text("SELECT id,user_id,request_id,status,events_json FROM ai_requests")).mappings().all()
    for row in rows:
        events = json.loads(row["events_json"])
        session_id = None
        has_attempt = False
        for event in events:
            if event.get("type") == "done" and event.get("turn_id"):
                session_id = connection.execute(sa.text(
                    "SELECT s.id FROM dialogue_turns t JOIN sessions s ON s.id=t.session_id "
                    "WHERE t.id=:turn AND s.user_id=:user"
                ), {"turn": event["turn_id"], "user": row["user_id"]}).scalar()
            if event.get("type") == "final" and event.get("attempt_id"):
                attempt = connection.execute(sa.text(
                    "SELECT session_id FROM attempts WHERE id=:attempt AND user_id=:user"
                ), {"attempt": event["attempt_id"], "user": row["user_id"]}).first()
                if attempt is not None:
                    has_attempt = True
                    session_id = session_id or attempt.session_id
        if session_id is not None:
            connection.execute(sa.text("UPDATE ai_requests SET session_id=:session WHERE id=:id"), {"session": session_id, "id": row["id"]})
        elif not has_attempt:
            # Incomplete legacy snapshots cannot be attributed to a session. Preserve errors only.
            errors = [event for event in events if event.get("type") == "error"]
            if not errors:
                errors = [{"type": "error", "code": "migration_interrupted", "request_id": row["request_id"]}]
            connection.execute(sa.text("UPDATE ai_requests SET events_json=:events,status='failed' WHERE id=:id"), {
                "events": json.dumps(errors, ensure_ascii=False), "id": row["id"],
            })


def downgrade() -> None:
    with op.batch_alter_table("ai_requests") as batch:
        batch.drop_index("ix_ai_requests_session_id")
        batch.drop_constraint("fk_ai_requests_session_id", type_="foreignkey")
        batch.drop_column("session_id")
    op.drop_index("ix_sessions_user_id_id", table_name="sessions")
    with op.batch_alter_table("sessions") as batch:
        batch.drop_column("title")
