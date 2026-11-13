from uuid import uuid4
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
    payload = {"card_id": card["id"], "rating": 3, "request_id": str(uuid4())}
    assert client.post("/reviews", headers=other, json=payload).status_code == 404
    assert client.post("/reviews", headers=owner, json={**payload, "rating": 5}).status_code == 422

    response = client.post("/reviews", headers=owner, json=payload)
    assert response.status_code == 200
    assert client.post("/reviews", headers=owner, json=payload).json() == response.json()
    assert client.post("/reviews", headers=owner, json={**payload, "rating": 2}).status_code == 409
    assert response.json()["interval_days"] == 3
    assert response.json()["card"]["stability"] == pytest.approx(3.173)
    assert client.get("/cards/due", headers=owner).json() == []

    response = client.post("/reviews", headers=owner, json={**payload, "rating": 1, "request_id": str(uuid4())})
    assert response.status_code == 200
    assert response.json()["card"]["stability"] < 3.173
    assert response.json()["interval_seconds"] == 600
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
        events = []
        while not events or events[-1]["type"] != "final":
            events.append(socket.receive_json())
        assert events[0]["type"] == "transcript"
        assert any(event["type"] == "done" for event in events)
    assert speech_paths == ["/transcribe", "/assess"]

    payload = {"session_id": session_id, "text": "I went to Hanoi."}
    assert client.post("/chat/stream", headers=other, json=payload).status_code == 404
    response = client.post("/chat/stream", headers=owner, json=payload)
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: done" in response.text
    assert prompts[1][1] == {"role": "user", "content": "I go yesterday."}
    progress = client.get("/progress", headers=owner).json()
    assert progress["attempts"] == 1
    assert progress["phoneme_averages"] == {"ɡ": 50}
    assert progress["timezone"] == "Asia/Ho_Chi_Minh"
    assert progress["daily"][0]["attempts"] == 1
    assert client.get(f"/sessions/{session_id}/turns", headers=owner).json()[0]["text"] == "I go yesterday."
    assert client.get(f"/sessions/{session_id}/turns", headers=other).status_code == 404
    assert client.get("/progress", headers=other).json()["attempts"] == 0
    with Session(engine) as db:
        assert len(list(db.scalars(select(DialogueTurn)))) == 2


def test_incomplete_talk_is_not_saved(api, monkeypatch):
    client, engine = api
    headers = register(client, "talk@example.com")
    session_id = client.post("/sessions", headers=headers, json={}).json()["id"]

    async def broken_stream(messages):
        yield "Partial "
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


def test_talk_lease_history_and_word_limit(api, monkeypatch):
    from app.dialogue import reserve_turn, release_turn
    from app.models import User
    client, engine = api
    headers = register(client, "lease@example.com")
    session_id = client.post("/sessions", headers=headers, json={}).json()["id"]
    with Session(engine) as db:
        user_id = db.scalar(select(User.id))
        _, token = reserve_turn(db, user_id, session_id)
    payload = {"session_id": session_id, "text": "Hello"}
    assert client.post("/chat/stream", headers=headers, json=payload).status_code == 409
    with Session(engine) as db:
        release_turn(db, session_id, token)

    async def long_reply(messages):
        for _ in range(60):
            yield "word "
    monkeypatch.setattr(llm, "stream_reply", long_reply)
    response = client.post("/chat/stream", headers=headers, json=payload)
    assert "event: done" in response.text
    history = client.get(f"/sessions/{session_id}/turns", headers=headers).json()
    assert len(history[0]["reply"].split()) == 40
    assert client.get("/sessions", headers=headers).json()[0]["id"] == session_id
    assert client.post("/chat/stream", headers=headers, json=payload).status_code == 200


def test_assessment_failure_does_not_block_talk(api, monkeypatch):
    from app.speech import SpeechError
    client, _ = api
    headers = register(client, "speech-error@example.com")
    session_id = client.post("/sessions", headers=headers, json={}).json()["id"]
    async def broken_assessment(*args):
        raise SpeechError("unavailable")
    async def reply(messages):
        yield "Hello there. "
    monkeypatch.setattr("app.audio.request_audio", broken_assessment)
    monkeypatch.setattr(llm, "stream_reply", reply)
    with client.websocket_connect("/ws/audio") as ws:
        ws.send_bytes(b"audio")
        ws.receive_json()
        ws.send_json({
            "type": "end", "token": headers["Authorization"].split()[1],
            "text": "Hello", "session_id": session_id,
        })
        events = []
        while not events or events[-1].get("code") != "assessment_unavailable":
            events.append(ws.receive_json())
        assert any(event["type"] == "done" for event in events)
    assert client.get("/progress", headers=headers).json()["attempts"] == 0
