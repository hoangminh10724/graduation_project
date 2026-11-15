import asyncio
import json
from datetime import datetime, timezone
from tempfile import SpooledTemporaryFile

import pytest
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from starlette.requests import ClientDisconnect

from app import personal_data
from app.models import Attempt, Card, Deck, DialogueTurn, Review, Session as TalkSession, StudyItem, StudySession, User
from test_cards import api, register


def test_export_owned_learning_data_without_auth_secrets(api, monkeypatch):
    client, engine = api
    owner = register(client, "export@example.test")
    register(client, "outsider@example.test")
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    with Session(engine) as db:
        for user in db.scalars(select(User)).all():
            marker = "PRIVATE_OUTSIDER" if user.email.startswith("outsider") else "Xin chào θ"
            deck = Deck(user_id=user.id, name=marker, description="example")
            talk = TalkSession(user_id=user.id, title=marker)
            db.add_all([deck, talk])
            db.flush()
            card = Card(user_id=user.id, deck_id=deck.id, front=marker, back="hello")
            study = StudySession(user_id=user.id, request_id=str(user.id), selection_json='{}', status="completed", started_at=now, finished_at=now)
            db.add_all([card, study])
            db.flush()
            db.add_all([
                Review(card_id=card.id, rating=3, study_session_id=study.id),
                DialogueTurn(session_id=talk.id, learner_text=marker, tutor_text="hello"),
                Attempt(user_id=user.id, text=marker, sentence_score=70, detail_json='{"words":[]}'),
                StudyItem(study_session_id=study.id, card_id=card.id, position=0, expected_due=now, state="reviewed", rating=3, reviewed_at=now),
            ])
        db.commit()
    files = []
    original = personal_data.build_export

    def capture(*args):
        file = original(*args)
        files.append(file)
        return file

    monkeypatch.setattr(personal_data, "build_export", capture)
    response = client.post("/me/export", headers=owner, json={"current_password": "test-pass"})
    assert response.status_code == 200
    data = response.json()
    assert data["schema_version"] == 1 and data["profile"]["email"] == "export@example.test"
    assert "PRIVATE_OUTSIDER" not in response.text
    for name in ("decks", "cards", "reviews", "talk_sessions", "talk_turns", "pronunciation_attempts", "study_sessions", "study_items"):
        assert len(data[name]) == 1
    assert data["cards"][0]["front"] == "Xin chào θ"
    assert data["talk_turns"][0]["completed_at"] is None
    assert data["reviews"][0]["reviewed_at"].endswith("Z")
    for secret in ("password_hash", "token_version", "refresh_digest", "turn_token", "busy_until", "test-pass", "login_sessions", "account_actions"):
        assert secret not in response.text
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["content-disposition"].startswith("attachment;")
    assert int(response.headers["content-length"]) == len(response.content)
    assert files and files[0].closed


def test_export_password_limit_and_size_failure(api, monkeypatch):
    client, _ = api
    owner = register(client, "export-limits@example.test")
    assert client.post("/me/export", json={"current_password": "test-pass"}).status_code == 401
    assert client.post("/me/export", headers=owner, json={"current_password": "θ" * 37}).status_code == 422
    assert client.post("/me/export", headers=owner, json={"current_password": "wrong"}).status_code == 401
    files = []

    def temporary_file(**kwargs):
        file = SpooledTemporaryFile(**kwargs)
        files.append(file)
        return file

    monkeypatch.setattr(personal_data, "SpooledTemporaryFile", temporary_file)
    monkeypatch.setattr(personal_data, "MAX_EXPORT_BYTES", 10)
    response = client.post("/me/export", headers=owner, json={"current_password": "test-pass"})
    assert response.status_code == 413 and files[0].closed
    monkeypatch.setattr(personal_data, "MAX_EXPORT_BYTES", 50 * 1024 * 1024)
    assert client.post("/me/export", headers=owner, json={"current_password": "test-pass"}).status_code == 200
    response = client.post("/me/export", headers=owner, json={"current_password": "test-pass"})
    assert response.status_code == 429 and "retry-after" in response.headers


def test_export_closes_file_when_download_disconnects():
    file = SpooledTemporaryFile(mode="w+b")
    file.write(json.dumps({"ok": True}).encode())
    response = personal_data.ExportResponse(file)

    async def send(message):
        raise OSError("disconnected")

    async def receive():
        return {"type": "http.disconnect"}

    with pytest.raises(ClientDisconnect):
        asyncio.run(response({"type": "http", "asgi": {"spec_version": "2.4"}}, receive, send))
    assert file.closed


def test_export_uses_one_snapshot_during_concurrent_edit(api, monkeypatch):
    client, engine = api
    owner = register(client, "export-snapshot@example.test")
    card = client.post("/cards", headers=owner, json={"front": "before", "back": "test"}).json()
    with engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA journal_mode=WAL")
    original = personal_data.export_queries

    def queries(user_id):
        for name, query in original(user_id):
            if name == "cards":
                with Session(engine) as writer:
                    writer.execute(update(Card).where(Card.id == card["id"]).values(front="after"))
                    writer.commit()
            yield name, query

    monkeypatch.setattr(personal_data, "export_queries", queries)
    response = client.post("/me/export", headers=owner, json={"current_password": "test-pass"})
    assert response.status_code == 200
    assert response.json()["cards"][0]["front"] == "before"
    assert client.get(f"/cards/{card['id']}", headers=owner).json()["front"] == "after"
