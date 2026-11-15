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
        socket.send_json({"type": "auth", "token": owner["Authorization"].split()[1]})
        assert socket.receive_json()["type"] == "authenticated"
        socket.send_bytes(b"audio")
        assert socket.receive_json() == {"type": "partial", "received_bytes": 5}
        socket.send_json({"type": "end", "request_id": str(uuid4()), "token": owner["Authorization"].split()[1], "session_id": session_id})
        events = []
        while not events or events[-1]["type"] != "final":
            events.append(socket.receive_json())
        assert events[0]["type"] == "transcript"
        assert any(event["type"] == "done" for event in events)
    assert speech_paths == ["/transcribe", "/assess"]

    payload = {"request_id": str(uuid4()), "session_id": session_id, "text": "I went to Hanoi."}
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
    assert client.get(f"/sessions/{session_id}/turns", headers=owner).json()["items"][-1]["text"] == "I go yesterday."
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
        "/chat/stream", headers=headers, json={"request_id": str(uuid4()), "session_id": session_id, "text": "Hello"}
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
    payload = {"request_id": str(uuid4()), "session_id": session_id, "text": "Hello"}
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
    assert len(history["items"][0]["reply"].split()) == 40
    assert client.get("/sessions", headers=headers).json()["items"][0]["id"] == session_id
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
        ws.send_json({"type": "auth", "token": headers["Authorization"].split()[1]})
        assert ws.receive_json()["type"] == "authenticated"
        ws.send_bytes(b"audio")
        ws.receive_json()
        ws.send_json({
            "type": "end", "request_id": str(uuid4()), "token": headers["Authorization"].split()[1],
            "text": "Hello", "session_id": session_id,
        })
        events = []
        while not events or events[-1].get("code") != "assessment_unavailable":
            events.append(ws.receive_json())
        assert any(event["type"] == "done" for event in events)
    assert client.get("/progress", headers=headers).json()["attempts"] == 0


def test_expired_turn_cannot_write_after_new_reservation(api):
    from datetime import datetime, timedelta, timezone
    from fastapi import HTTPException
    from app.dialogue import reserve_turn, release_turn, store_turn
    from app.models import User, Session as TalkSession
    client, engine = api
    headers = register(client, "expired@example.com")
    session_id = client.post("/sessions", headers=headers, json={}).json()["id"]
    with Session(engine) as db:
        user_id = db.scalar(select(User.id))
        _, old_token = reserve_turn(db, user_id, session_id)
        db.get(TalkSession, session_id).busy_until = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=1)
        db.commit()
        _, new_token = reserve_turn(db, user_id, session_id)
        with pytest.raises(HTTPException) as error:
            store_turn(db, session_id, "old", "stale", old_token)
        assert error.value.status_code == 409
        release_turn(db, session_id, old_token)
        assert db.get(TalkSession, session_id).turn_token == new_token
        store_turn(db, session_id, "new", "valid", new_token)
        assert list(db.scalars(select(DialogueTurn.tutor_text))) == ["valid"]


def test_missing_audio_session_releases_transaction(api):
    from app.audio import AudioEnd, prepare_turn
    from fastapi import HTTPException
    client, engine = api
    headers = register(client, "transaction@example.com")
    with Session(engine) as db:
        payload = AudioEnd(type="end", request_id=uuid4(), session_id=999)
        with pytest.raises(HTTPException):
            prepare_turn(db, payload, headers["Authorization"].split()[1])
        assert not db.in_transaction()


def test_login_rate_limit_has_retry_header(api):
    client, _ = api
    payload = {"email": "absent@example.com", "password": "invalid-pass"}
    for _ in range(10):
        assert client.post("/auth/login", json=payload).status_code == 401
    response = client.post("/auth/login", json=payload)
    assert response.status_code == 429
    assert 1 <= int(response.headers["Retry-After"]) <= 60


def test_deck_card_management_and_review_preview(api):
    client, engine = api
    owner = register(client, "cards-owner@example.com")
    other = register(client, "cards-other@example.com")
    deck_id = client.post("/decks", headers=owner, json={"name": "Travel"}).json()["id"]
    assert client.put(f"/decks/{deck_id}", headers=other, json={"name": "Changed"}).status_code == 404
    assert client.post("/cards", headers=other, json={
        "front": "bad", "back": "bad", "deck_id": deck_id,
    }).status_code == 404
    card = client.post("/cards", headers=owner, json={
        "front": "Train", "back": "Tàu hỏa", "deck_id": deck_id,
    }).json()
    card_id = card["id"]
    assert client.get(f"/cards/{card_id}", headers=other).status_code == 404
    assert client.patch(f"/cards/{card_id}", headers=other, json={"suspended": True}).status_code == 404
    assert client.get("/cards", headers=other).json()["items"] == []
    assert client.get("/cards?q=train", headers=owner).json()["items"][0]["id"] == card_id

    preview = client.get(f"/cards/{card_id}/schedule", headers=owner).json()
    assert [item["interval_seconds"] for item in preview["choices"]] == [600, 86400, 259200, 1382400]
    with Session(engine) as db:
        assert db.scalar(select(Review)) is None
    assert client.patch(f"/cards/{card_id}", headers=owner, json={"front": None}).status_code == 422
    assert client.patch(f"/cards/{card_id}", headers=owner, json={"suspended": True}).status_code == 200
    assert client.get("/cards/due", headers=owner).json() == []
    payload = {"card_id": card_id, "rating": 3, "request_id": str(uuid4())}
    assert client.post("/reviews", headers=owner, json=payload).status_code == 409
    client.patch(f"/cards/{card_id}", headers=owner, json={"suspended": False})
    result = client.post("/reviews", headers=owner, json=payload)
    assert result.status_code == 200
    assert result.json()["interval_seconds"] == preview["choices"][2]["interval_seconds"]
    history = client.get(f"/cards/{card_id}/reviews", headers=owner).json()
    assert history["items"][0]["rating"] == 3
    assert client.get(f"/cards/{card_id}/reviews", headers=other).status_code == 404

    assert client.delete(f"/decks/{deck_id}", headers=other).status_code == 404
    assert client.delete(f"/decks/{deck_id}", headers=owner).status_code == 204
    retained = client.get(f"/cards/{card_id}", headers=owner).json()
    assert retained["deck_id"] is None
    assert retained["stability"] == 3.173
    assert client.delete(f"/cards/{card_id}", headers=other).status_code == 404
    assert client.delete(f"/cards/{card_id}", headers=owner).status_code == 204
    with Session(engine) as db:
        assert db.scalar(select(Review)) is None


def test_card_cursor_and_literal_search(api):
    client, _ = api
    headers = register(client, "pages@example.com")
    for front in ("100%", "travel", "plane"):
        assert client.post("/cards", headers=headers, json={"front": front, "back": front}).status_code == 201
    first = client.get("/cards?limit=2", headers=headers).json()
    second = client.get(f"/cards?limit=2&cursor={first['next_cursor']}", headers=headers).json()
    assert len(first["items"]) == 2 and len(second["items"]) == 1
    assert second["next_cursor"] is None
    assert len({card["id"] for card in first["items"] + second["items"]}) == 3
    assert len(client.get("/cards", headers=headers, params={"q": "%"}).json()["items"]) == 1
    assert client.get("/cards?limit=10000", headers=headers).status_code == 422
