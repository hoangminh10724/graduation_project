from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from app.db import get_engine


def test_initial_migration(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    config = Config(Path(__file__).resolve().parents[1] / "alembic.ini")
    engine = get_engine()
    tables = {
        "users", "sessions", "cards", "reviews", "attempts", "dialogue_turns",
        "rate_limits", "decks", "login_sessions", "used_refresh_tokens", "ai_requests",
    }
    try:
        command.upgrade(config, "0004_rate_limits")
        with engine.begin() as connection:
            connection.execute(text("INSERT INTO users (id,email,password_hash) VALUES (1,'old@example.test','unused')"))
            connection.execute(text(
                "INSERT INTO cards (id,user_id,front,back,stability,difficulty,due) "
                "VALUES (1,1,'hello','xin chao',3.173,5.0,'2026-11-20 12:00:00')"
            ))
            connection.execute(text(
                "INSERT INTO attempts (id,user_id,text,sentence_score,detail_json) "
                "VALUES (1,1,'old sentence',72,'{}')"
            ))
        command.upgrade(config, "head")
        with engine.connect() as connection:
            row = connection.execute(text("SELECT stability, suspended, deck_id, due FROM cards WHERE id=1")).one()
            assert row.stability == 3.173
            assert not row.suspended and row.deck_id is None
            assert str(row.due).startswith("2026-11-20")
            attempt = connection.execute(text(
                "SELECT text,sentence_score,reference_text,transcript,session_id FROM attempts WHERE id=1"
            )).one()
            assert attempt.text == "old sentence" and attempt.sentence_score == 72
            assert attempt.reference_text is None and attempt.transcript is None and attempt.session_id is None
        assert tables <= set(inspect(engine).get_table_names())
        command.check(config)

        command.downgrade(config, "base")
        assert tables.isdisjoint(inspect(engine).get_table_names())
    finally:
        engine.dispose()
        get_engine.cache_clear()
