import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier, Event
from uuid import uuid4

import pytest
from anyio import CancelScope
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import requests
from app.dialogue import release_turn, reserve_turn, store_turn
from app.cancellation import CancellationGuard, guarded_stream
from app.models import AIRequest, Attempt, DialogueTurn, User, Session as TalkSession
from app.progress import store_attempt
from test_cards import api, register
from test_requests import sse_events


@pytest.mark.parametrize("stage", ["stt", "llm", "assessment"])
def test_cancel_audio_during_external_io_preserves_committed_results(api, monkeypatch, stage):
    client, engine = api
    owner = register(client, "cancel-audio@example.com")
    other = register(client, "not-owner@example.com")
    session_id = client.post("/sessions", headers=owner, json={}).json()["id"]
    request_id = uuid4()
    started, closed = Event(), Event()

    async def wait_for_cancel():
        started.set()
        try:
            await asyncio.wait_for(asyncio.Future(), timeout=5)
        finally:
            closed.set()

    async def speech(path, *args):
        if (stage == "stt" and path == "/transcribe") or (stage == "assessment" and path == "/assess"):
            await wait_for_cancel()
        return {"text": "Hello"} if path == "/transcribe" else {"sentence_score": 70, "words": []}

    async def reply(messages):
        yield "Hello there. "
        if stage == "llm":
            await wait_for_cancel()

    monkeypatch.setattr("app.audio.request_audio", speech)
    monkeypatch.setattr("app.llm.stream_reply", reply)
    with client.websocket_connect("/ws/audio") as ws:
        ws.send_json({"type": "auth", "token": owner["Authorization"].split()[1]})
        assert ws.receive_json()["type"] == "authenticated"
        ws.send_bytes(b"audio")
        ws.receive_json()
        ws.send_json({"type": "end", "request_id": str(request_id), "session_id": session_id})
        assert started.wait(timeout=3)
        if stage == "assessment":
            while (event := ws.receive_json())["type"] != "done":
                assert event["type"] != "error"
        assert client.post(f"/requests/{request_id}/cancel", headers=other).status_code == 404
        cancelled = client.post(f"/requests/{request_id}/cancel", headers=owner)
        assert cancelled.status_code == 200 and cancelled.json()["status"] == "cancelled"
        assert cancelled.json()["events"][-1]["code"] == "request_cancelled"
        assert client.post(f"/requests/{request_id}/cancel", headers=owner).json() == cancelled.json()
        while (event := ws.receive_json())["type"] != "error":
            assert event["type"] != "final"
        assert event["code"] == "request_cancelled" and event["request_id"] == str(request_id)
        assert closed.wait(timeout=3)
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(Attempt)) == 0
        assert db.scalar(select(func.count()).select_from(DialogueTurn)) == (1 if stage == "assessment" else 0)
        assert db.get(TalkSession, session_id).turn_token is None
    if stage == "assessment":
        assert any(event["type"] == "done" for event in cancelled.json()["events"])

    async def new_reply(messages):
        yield "A new turn."

    monkeypatch.setattr("app.llm.stream_reply", new_reply)
    new_id = str(uuid4())
    response = client.post("/chat/stream", headers=owner, json={"request_id": new_id, "session_id": session_id, "text": "Again"})
    assert response.status_code == 200 and sse_events(response)[-1]["type"] == "done"
    assert client.post(f"/requests/{new_id}/cancel", headers=owner).json()["status"] == "completed"
    assert client.post(f"/requests/{request_id}/cancel").status_code == 401


def test_cancel_live_sse_closes_model_stream_and_does_not_save_partial_text(api, monkeypatch):
    client, engine = api
    owner = register(client, "cancel-sse@example.com")
    session_id = client.post("/sessions", headers=owner, json={}).json()["id"]
    request_id = str(uuid4())
    started, closed = Event(), Event()

    async def reply(messages):
        try:
            yield "Partial "
            started.set()
            await asyncio.wait_for(asyncio.Future(), timeout=5)
        finally:
            closed.set()

    monkeypatch.setattr("app.llm.stream_reply", reply)
    with ThreadPoolExecutor(max_workers=1) as pool:
        response = pool.submit(client.post, "/chat/stream", headers=owner, json={
            "request_id": request_id, "session_id": session_id, "text": "Hello",
        })
        assert started.wait(timeout=3)
        assert client.post(f"/requests/{request_id}/cancel", headers=owner).json()["status"] == "cancelled"
        events = sse_events(response.result(timeout=4))
    assert events[-1]["code"] == "request_cancelled"
    assert closed.is_set() and not any(event["type"] == "done" for event in events)
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(DialogueTurn)) == 0
        assert db.get(TalkSession, session_id).turn_token is None
    repeated = client.post("/chat/stream", headers=owner, json={"request_id": request_id, "session_id": session_id, "text": "Hello"})
    assert sse_events(repeated)[-1]["code"] == "request_cancelled"
    assert sse_events(repeated)[-1]["replayed"]


def test_cancelling_old_request_does_not_release_new_reservation(api):
    client, engine = api
    owner = register(client, "old-cancel@example.com")
    user_id = client.get("/me", headers=owner).json()["id"]
    session_id = client.post("/sessions", headers=owner, json={}).json()["id"]
    request_id = uuid4()
    with Session(engine) as db:
        old_id, _ = requests.claim(db, user_id, request_id, "audio", {"session_id": session_id})
        _, old_token = reserve_turn(db, user_id, session_id, commit=False)
        requests.bind_turn(db, old_id, old_token)
        db.commit()
        db.get(TalkSession, session_id).busy_until = requests.utcnow() - timedelta(seconds=1)
        db.commit()
        _, new_token = reserve_turn(db, user_id, session_id)
    assert client.post(f"/requests/{request_id}/cancel", headers=owner).json()["status"] == "cancelled"
    with Session(engine) as db:
        assert db.get(TalkSession, session_id).turn_token == new_token
        release_turn(db, session_id, old_token)
        assert db.get(TalkSession, session_id).turn_token == new_token
        with pytest.raises(HTTPException):
            store_turn(db, session_id, "late", "do not save", old_token, old_id)
        with pytest.raises(HTTPException) as error:
            store_attempt(db, user_id, "late", {"sentence_score": 70, "words": []}, session_id=session_id, request_record_id=old_id)
        assert error.value.detail == "request_cancelled"
        assert db.scalar(select(func.count()).select_from(Attempt)) == 0
        assert db.scalar(select(func.count()).select_from(DialogueTurn)) == 0


def test_cancellation_racing_commit_has_one_consistent_result(api):
    client, engine = api
    owner = register(client, "race-cancel@example.com")
    user_id = client.get("/me", headers=owner).json()["id"]
    session_id = client.post("/sessions", headers=owner, json={}).json()["id"]
    request_id = uuid4()
    with Session(engine) as db:
        record_id, _ = requests.claim(db, user_id, request_id, "chat", {"session_id": session_id})
        _, token = reserve_turn(db, user_id, session_id, commit=False)
        requests.bind_turn(db, record_id, token)
        db.commit()
    barrier = Barrier(2)

    def commit_worker():
        with Session(engine) as db:
            barrier.wait(timeout=3)
            try:
                return store_turn(db, session_id, "hello", "reply", token, record_id, True)["type"]
            except HTTPException:
                return "rejected"

    def cancel_worker():
        with Session(engine) as db:
            user = db.get(User, user_id)
            barrier.wait(timeout=3)
            return requests.cancel_request(request_id, user, db).status

    with ThreadPoolExecutor(max_workers=2) as pool:
        written, cancelled = pool.submit(commit_worker), pool.submit(cancel_worker)
        result, state = written.result(timeout=5), cancelled.result(timeout=5)
    assert (result, state) in {("done", "completed"), ("rejected", "cancelled")}
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(DialogueTurn)) == (1 if state == "completed" else 0)
        assert db.get(AIRequest, record_id).status == state


def test_stream_preserves_upstream_task_scopes_and_total_timeout(api):
    client, engine = api
    owner = register(client, "stream-scope@example.com")
    user_id = client.get("/me", headers=owner).json()["id"]
    with Session(engine) as db:
        record_id, _ = requests.claim(db, user_id, uuid4(), "chat", {})
        db.commit()
    closed = []

    async def source():
        task = asyncio.current_task()
        try:
            with CancelScope():
                async with asyncio.timeout(0.1):
                    yield "first"
                    assert asyncio.current_task() is task
                    yield "second"
                    await asyncio.sleep(5)
        finally:
            assert asyncio.current_task() is task
            closed.append(True)

    async def consume():
        received = []
        with pytest.raises(TimeoutError):
            async for token in guarded_stream(source(), CancellationGuard(engine, record_id)):
                received.append(token)
        assert received == ["first", "second"]

    asyncio.run(consume())
    assert closed == [True]


def test_stream_timeout_during_backpressure_does_not_hang_consumer(api):
    client, engine = api
    owner = register(client, "backpressure@example.com")
    user_id = client.get("/me", headers=owner).json()["id"]
    with Session(engine) as db:
        record_id, _ = requests.claim(db, user_id, uuid4(), "chat", {})
        db.commit()
    closed = []

    async def source():
        try:
            async with asyncio.timeout(0.05):
                for _ in range(10):
                    yield "token"
        finally:
            closed.append(True)

    async def consume():
        stream = guarded_stream(source(), CancellationGuard(engine, record_id))
        assert await anext(stream) == "token"
        await asyncio.sleep(0.1)
        with pytest.raises(TimeoutError, match="Upstream stream stopped"):
            async with asyncio.timeout(1):
                async for _ in stream:
                    pass
        await stream.aclose()

    asyncio.run(consume())
    assert closed == [True]
