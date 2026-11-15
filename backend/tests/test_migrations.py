from pathlib import Path
import json

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
        "rate_limits", "decks", "login_sessions", "used_refresh_tokens", "ai_requests", "account_actions",
        "study_sessions", "study_items",
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
            connection.execute(text("INSERT INTO reviews (id,card_id,rating) VALUES (1,1,3)"))
        command.upgrade(config, "0009_account_recovery")
        with engine.begin() as connection:
            connection.execute(text("INSERT INTO sessions (id,user_id,topic,cefr_level) VALUES (1,1,'Travel','A2')"))
            connection.execute(text("INSERT INTO dialogue_turns (id,session_id,learner_text,tutor_text) VALUES (1,1,'hello','hi')"))
            for identity, events in ((1, [{"type": "done", "turn_id": 1, "text": "hi"}]), (2, [{"type": "transcript", "text": "unlinked partial"}])):
                connection.execute(text(
                    "INSERT INTO ai_requests (id,user_id,request_id,kind,fingerprint,status,events_json,created_at,deadline) "
                    "VALUES (:id,1,:request,'chat',:fingerprint,'completed',:events,'2026-11-20 12:00:00','2026-11-20 12:04:00')"
                ), {"id": identity, "request": f"request-{identity}", "fingerprint": "a" * 64, "events": json.dumps(events)})
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
            assert not connection.execute(text("SELECT email_verified FROM users WHERE id=1")).scalar_one()
            assert connection.execute(text("SELECT title FROM sessions WHERE id=1")).scalar_one() == "Travel"
            assert connection.execute(text("SELECT session_id FROM ai_requests WHERE id=1")).scalar_one() == 1
            assert "unlinked partial" not in connection.execute(text("SELECT events_json FROM ai_requests WHERE id=2")).scalar_one()
            old_review = connection.execute(text("SELECT rating,study_session_id FROM reviews WHERE id=1")).one()
            assert old_review.rating == 3 and old_review.study_session_id is None
        assert tables <= set(inspect(engine).get_table_names())
        command.check(config)

        command.downgrade(config, "base")
        assert tables.isdisjoint(inspect(engine).get_table_names())
    finally:
        engine.dispose()
        get_engine.cache_clear()
