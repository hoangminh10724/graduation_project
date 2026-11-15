import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from uuid import uuid4

from anyio import CancelScope
import pytest
from fastapi import HTTPException, WebSocketDisconnect
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app import llm, requests
from app.audio import AudioEnd, complete_audio
from app.dialogue import ChatRequest, chat, reserve_turn, store_turn
from app.models import AIRequest, Attempt, Base, DialogueTurn, RateLimit, User, Session as TalkSession
from app.progress import store_attempt
from app.speech import SpeechError
from test_cards import api, register


def sse_events(response):
    return [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]


def test_chat_replay_conflict_ownership_and_failure(api, monkeypatch):
    client, engine = api
    owner = register(client, "requests@example.com")
    other = register(client, "other@example.com")
    session_id = client.post("/sessions", headers=owner, json={}).json()["id"]
    calls = []

    async def reply(messages):
        calls.append(messages)
        yield "Hello there. "

    monkeypatch.setattr(llm, "stream_reply", reply)
    payload = {"request_id": str(uuid4()), "session_id": session_id, "text": "Hello"}
    first = sse_events(client.post("/chat/stream", headers=owner, json=payload))
    second = sse_events(client.post("/chat/stream", headers=owner, json=payload))
    assert len(calls) == 1
    assert first[-1]["type"] == second[-1]["type"] == "done"
    assert first[-1]["turn_id"] == second[-1]["turn_id"]
    assert all(event["replayed"] for event in second)
    assert all(event["request_id"] == payload["request_id"] for event in first + second)
    status = client.get(f"/requests/{payload['request_id']}", headers=owner).json()
    assert status["status"] == "completed" and status["events"] == [first[-1]]
    assert client.get(f"/requests/{payload['request_id']}", headers=other).status_code == 404
    assert client.get(f"/requests/{payload['request_id']}").status_code == 401
    conflict = client.post("/chat/stream", headers=owner, json={**payload, "text": "Different"})
    assert conflict.status_code == 409 and conflict.json()["detail"] == "request_conflict"
    assert client.post("/chat/stream", headers=owner, json={"session_id": session_id, "text": "Hello"}).status_code == 422
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(DialogueTurn)) == 1
        assert db.scalar(select(RateLimit.hits).where(RateLimit.key.like("ai-turn:%"))) == 1

    async def broken(messages):
        calls.append(messages)
        yield "Incomplete "
        raise llm.LLMError("offline")

    monkeypatch.setattr(llm, "stream_reply", broken)
    failed = {**payload, "request_id": str(uuid4())}
    first_failure = sse_events(client.post("/chat/stream", headers=owner, json=failed))
    repeated_failure = sse_events(client.post("/chat/stream", headers=owner, json=failed))
    assert first_failure[-1]["code"] == repeated_failure[-1]["code"] == "llm_unavailable"
    assert len(calls) == 2
    assert all(event["type"] == "error" for event in repeated_failure)
    assert client.get(f"/requests/{failed['request_id']}", headers=owner).json()["status"] == "failed"


def test_running_expired_and_late_writer_cannot_commit(api):
    client, engine = api
    owner = register(client, "running@example.com")
    user_id = client.get("/me", headers=owner).json()["id"]
    session_id = client.post("/sessions", headers=owner, json={}).json()["id"]
    request_id = uuid4()
    inputs = {"session_id": session_id, "text": "Hello"}
    with Session(engine) as db:
        record_id, _ = requests.claim(db, user_id, request_id, "chat", inputs)
        _, token = reserve_turn(db, user_id, session_id, commit=False)
        db.commit()
    payload = {**inputs, "request_id": str(request_id)}
    running = client.post("/chat/stream", headers=owner, json=payload)
    assert running.status_code == 409 and running.json()["detail"] == "request_processing"
    assert running.headers["retry-after"] == "2"
    assert client.get(f"/requests/{request_id}", headers=owner).json()["status"] == "running"
    with Session(engine) as db:
        db.get(AIRequest, record_id).deadline = requests.utcnow() - timedelta(seconds=1)
        db.commit()
        with pytest.raises(HTTPException):
            store_turn(db, session_id, "late", "must not persist", token, record_id, True)
        with pytest.raises(HTTPException):
            store_attempt(db, user_id, "late", {"sentence_score": 75, "words": []}, request_record_id=record_id)
        assert db.scalar(select(func.count()).select_from(DialogueTurn)) == 0
        assert db.scalar(select(func.count()).select_from(Attempt)) == 0
    expired = client.get(f"/requests/{request_id}", headers=owner).json()
    assert expired["status"] == "failed" and expired["events"][-1]["code"] == "request_expired"
    assert sse_events(client.post("/chat/stream", headers=owner, json=payload))[-1]["code"] == "request_expired"


class Transport:
    def __init__(self, disconnect_at=None):
        self.events = []
        self.disconnect_at = disconnect_at

    async def send_json(self, event):
        if event["type"] == self.disconnect_at:
            raise WebSocketDisconnect()
        self.events.append(event)


@pytest.mark.parametrize("disconnect_at", [None, "done", "final"])
def test_audio_retry_recovers_committed_results_after_disconnect(api, monkeypatch, disconnect_at):
    client, engine = api
    owner = register(client, "audio-request@example.com")
    session_id = client.post("/sessions", headers=owner, json={}).json()["id"]
    token = owner["Authorization"].split()[1]
    calls = []

    async def speech(path, *args):
        calls.append(path)
        return {"sentence_score": 80, "words": [], "hints": ["Keep practising."]}

    async def reply(messages):
        calls.append("llm")
        yield "Hello there. "

    monkeypatch.setattr("app.audio.request_audio", speech)
    monkeypatch.setattr(llm, "stream_reply", reply)
    payload = AudioEnd(type="end", request_id=uuid4(), text="Hello", session_id=session_id)
    transport = Transport(disconnect_at)
    with Session(engine) as db:
        if disconnect_at:
            with pytest.raises(WebSocketDisconnect):
                asyncio.run(complete_audio(transport, db, payload, b"audio", token))
        else:
            asyncio.run(complete_audio(transport, db, payload, b"audio", token))
    before_calls = list(calls)
    replay = Transport()
    with Session(engine) as db:
        asyncio.run(complete_audio(replay, db, payload, b"audio", token))
        assert calls == before_calls
        assert db.scalar(select(func.count()).select_from(DialogueTurn)) == 1
        assert db.scalar(select(func.count()).select_from(Attempt)) == (0 if disconnect_at == "done" else 1)
        assert db.get(TalkSession, session_id).turn_token is None
        with pytest.raises(HTTPException) as conflict:
            asyncio.run(complete_audio(Transport(), db, payload, b"different audio", token))
        assert conflict.value.detail == "request_conflict"
    assert all(event["replayed"] for event in replay.events)
    status = client.get(f"/requests/{payload.request_id}", headers=owner).json()
    if disconnect_at == "done":
        assert status["status"] == "failed"
        assert status["events"][-1]["code"] == "request_interrupted"
    else:
        assert status["status"] == "completed"
        assert status["events"][-1]["type"] == "coaching"
        final = next(event for event in replay.events if event["type"] == "final")
        assert client.get(f"/attempts/{final['attempt_id']}", headers=owner).status_code == 200


@pytest.mark.parametrize("cancelled", [False, True])
def test_chat_disconnect_closes_upstream_and_releases_lease(api, monkeypatch, cancelled):
    client, engine = api
    owner = register(client, "disconnect@example.com")
    user_id = client.get("/me", headers=owner).json()["id"]
    session_id = client.post("/sessions", headers=owner, json={}).json()["id"]
    closed = []

    async def reply(messages):
        try:
            yield "Partial "
            yield "reply "
        finally:
            closed.append(True)

    monkeypatch.setattr(llm, "stream_reply", reply)
    payload = ChatRequest(request_id=uuid4(), session_id=session_id, text="Hello")
    with Session(engine) as db:
        response = chat(payload, db.get(User, user_id), db)

        async def disconnect():
            assert "event: token" in await anext(response.body_iterator)
            with CancelScope() as scope:
                if cancelled:
                    scope.cancel()
                await response.body_iterator.aclose()

        asyncio.run(disconnect())
        assert closed == [True]
        assert db.get(TalkSession, session_id).turn_token is None
        assert db.scalar(select(func.count()).select_from(DialogueTurn)) == 0
    status = client.get(f"/requests/{payload.request_id}", headers=owner).json()
    assert status["status"] == "failed" and status["events"][-1]["code"] == "request_interrupted"


@pytest.mark.parametrize("failure", ["stt", "llm", "assessment"])
def test_audio_failure_replay_preserves_partial_success(api, monkeypatch, failure):
    client, engine = api
    owner = register(client, "partial@example.com")
    session_id = client.post("/sessions", headers=owner, json={}).json()["id"]
    token = owner["Authorization"].split()[1]
    calls = []

    async def speech(path, *args):
        calls.append(path)
        if (failure == "stt" and path == "/transcribe") or (failure == "assessment" and path == "/assess"):
            raise SpeechError("offline")
        return {"text": "Hello"} if path == "/transcribe" else {"sentence_score": 80, "words": []}

    async def reply(messages):
        calls.append("llm")
        if failure == "llm":
            raise llm.LLMError("offline")
        yield "Hello there. "

    monkeypatch.setattr("app.audio.request_audio", speech)
    monkeypatch.setattr(llm, "stream_reply", reply)
    payload = AudioEnd(type="end", request_id=uuid4(), session_id=session_id)
    with Session(engine) as db:
        if failure == "stt":
            with pytest.raises(SpeechError):
                asyncio.run(complete_audio(Transport(), db, payload, b"audio", token))
        else:
            asyncio.run(complete_audio(Transport(), db, payload, b"audio", token))
    first_calls = list(calls)
    replay = Transport()
    with Session(engine) as db:
        asyncio.run(complete_audio(replay, db, payload, b"audio", token))
        assert calls == first_calls
        assert db.scalar(select(func.count()).select_from(Attempt)) == (1 if failure == "llm" else 0)
        assert db.scalar(select(func.count()).select_from(DialogueTurn)) == (1 if failure == "assessment" else 0)
        assert db.get(TalkSession, session_id).turn_token is None
    status = client.get(f"/requests/{payload.request_id}", headers=owner).json()
    assert status["status"] == "failed"
    assert any(event["type"] == "error" for event in replay.events)


def test_concurrent_request_claims_accept_exactly_one_worker(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'requests.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(User(id=1, email="race@example.test", password_hash="unused"))
        db.commit()
    request_id = uuid4()
    barrier = Barrier(2)

    def worker():
        with Session(engine) as db:
            barrier.wait(timeout=5)
            try:
                record_id, replay = requests.claim(db, 1, request_id, "chat", {"text": "hello"})
                db.commit()
                return "accepted"
            except HTTPException as error:
                return error.detail

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: worker(), range(2)))
        assert sorted(results) == ["accepted", "request_processing"]
        with Session(engine) as db:
            assert db.scalar(select(func.count()).select_from(AIRequest)) == 1
    finally:
        engine.dispose()
