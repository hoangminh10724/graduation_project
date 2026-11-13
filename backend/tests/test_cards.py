import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import llm
from app.db import get_db
from app.main import app
from app.models import Base, DialogueTurn, Review


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-with-at-least-32-bytes")
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)

    def db_override():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = db_override
    try:
        with TestClient(app) as client:
            yield client, engine
    finally:
        app.dependency_overrides.pop(get_db)
        engine.dispose()


def register(client, email):
    response = client.post("/auth/register", json={"email": email, "password": "test-pass"})
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_flashcard_flow_and_ownership(api):
    client, engine = api
    assert client.get("/cards/due").status_code == 401
    owner = register(client, "one@example.com")
    other = register(client, "two@example.com")

    response = client.post("/cards", headers=owner, json={"front": "hello", "back": "xin chào"})
    assert response.status_code == 201
    card = response.json()
    assert client.get("/cards/due", headers=owner).json() == [card]
    assert client.get("/cards/due", headers=other).json() == []
    payload = {"card_id": card["id"], "rating": 3}
    assert client.post("/reviews", headers=other, json=payload).status_code == 404
    assert client.post("/reviews", headers=owner, json={**payload, "rating": 5}).status_code == 422

    response = client.post("/reviews", headers=owner, json=payload)
    assert response.status_code == 200
    assert response.json()["interval_days"] == 3
    assert response.json()["card"]["stability"] == pytest.approx(3.173)
    assert client.get("/cards/due", headers=owner).json() == []

    response = client.post("/reviews", headers=owner, json={**payload, "rating": 1})
    assert response.status_code == 200
    assert response.json()["card"]["stability"] < 3.173
    with Session(engine) as db:
        assert list(db.scalars(select(Review.rating).order_by(Review.id))) == [3, 1]


def test_login_and_duplicate_registration(api):
    client, _ = api
    register(client, "user@example.com")
    credentials = {"email": "USER@example.com", "password": "test-pass"}
    assert client.post("/auth/register", json=credentials).status_code == 409
    assert client.post("/auth/login", json=credentials).status_code == 200
    assert client.post("/auth/login", json={**credentials, "password": "wrong-pass"}).status_code == 401


def test_audio_talk_and_progress(api, monkeypatch):
    client, engine = api
    owner = register(client, "owner@example.com")
    other = register(client, "other@example.com")
    session = client.post("/sessions", headers=owner, json={"topic": "Travel", "cefr_level": "B1"})
    assert session.status_code == 201
    session_id = session.json()["id"]
    speech_paths = []
    prompts = []

    async def fake_audio(path, data, media_type, text=None):
        speech_paths.append(path)
        assert data == b"audio" and media_type == "audio/webm"
        if path == "/transcribe":
            return {"text": "I go yesterday."}
        assert text == "I go yesterday."
        return {"sentence_score": 75, "words": [
            {"word": "go", "score": 50, "phonemes": [{"ipa": "ɡ", "score": 50, "start": 0, "end": 1}]},
        ]}

    async def fake_llm(messages):
        prompts.append(messages)
        yield "You went yesterday. "
        yield "Where did you go?"

    monkeypatch.setattr("app.audio.request_audio", fake_audio)
    monkeypatch.setattr("app.llm.stream_reply", fake_llm)
    with client.websocket_connect("/ws/audio") as socket:
        socket.send_bytes(b"audio")
        assert socket.receive_json() == {"type": "partial", "received_bytes": 5}
        socket.send_json({"type": "end", "token": owner["Authorization"].split()[1], "session_id": session_id})
        assert socket.receive_json()["type"] == "final"
        assert socket.receive_json()["type"] == "token"
        assert socket.receive_json()["type"] == "token"
        assert socket.receive_json()["type"] == "done"
    assert speech_paths == ["/transcribe", "/assess"]
    assert "/ɡ/" in prompts[0][-1]["content"]

    payload = {"session_id": session_id, "text": "I went to Hanoi."}
    assert client.post("/chat/stream", headers=other, json=payload).status_code == 404
    response = client.post("/chat/stream", headers=owner, json=payload)
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: done" in response.text
    assert prompts[1][1] == {"role": "user", "content": "I go yesterday."}
    assert client.get("/progress", headers=owner).json() == {
        "attempts": 1, "streak_days": 1, "phoneme_averages": {"ɡ": 50},
    }
    assert client.get("/progress", headers=other).json()["attempts"] == 0
    with Session(engine) as db:
        assert len(list(db.scalars(select(DialogueTurn)))) == 2


def test_incomplete_talk_is_not_saved(api, monkeypatch):
    client, engine = api
    headers = register(client, "talk@example.com")
    session_id = client.post("/sessions", headers=headers, json={}).json()["id"]

    async def broken_stream(messages):
        yield "Partial"
        raise llm.LLMError("Connection lost")

    monkeypatch.setattr(llm, "stream_reply", broken_stream)
    response = client.post(
        "/chat/stream", headers=headers, json={"session_id": session_id, "text": "Hello"}
    )
    assert "event: token" in response.text
    assert "event: error" in response.text
    assert "event: done" not in response.text
    with Session(engine) as db:
        assert db.scalar(select(DialogueTurn)) is None
