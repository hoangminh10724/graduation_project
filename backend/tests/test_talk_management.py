import json
from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app import requests
from app.dialogue import reserve_turn, store_turn
from app.models import AIRequest, Attempt, DialogueTurn, Session as TalkSession, User
from app.progress import store_attempt
from test_cards import api, register


def test_session_edit_search_pagination_and_ownership(api, monkeypatch):
    client, _ = api
    owner = register(client, "talk-owner@example.com")
    other = register(client, "talk-other@example.com")
    first = client.post("/sessions", headers=owner, json={"topic": "Travel"}).json()
    second = client.post("/sessions", headers=owner, json={"title": "100% ready", "topic": "Food"}).json()
    assert first["title"] == "Travel" and not first["processing"] and first["started_at"].endswith("Z")
    page = client.get("/sessions?limit=1", headers=owner).json()
    assert [row["id"] for row in page["items"]] == [second["id"]]
    assert page["next_cursor"] == second["id"]
    client.post("/sessions", headers=owner, json={})
    next_page = client.get(f"/sessions?limit=1&before_id={page['next_cursor']}", headers=owner).json()
    assert [row["id"] for row in next_page["items"]] == [first["id"]] and next_page["next_cursor"] is None
    assert [row["id"] for row in client.get("/sessions", headers=owner, params={"q": "%"}).json()["items"]] == [second["id"]]
    assert client.get("/sessions", headers=other).json()["items"] == []
    path = f"/sessions/{first['id']}"
    for method, kwargs in (("get", {}), ("patch", {"json": {"title": "No"}}), ("delete", {})):
        assert getattr(client, method)(path, headers=other, **kwargs).status_code == 404
    assert client.get(path).status_code == 401
    for query in ("limit=101", "limit=0", "before_id=0"):
        assert client.get(f"/sessions?{query}", headers=owner).status_code == 422
    for payload in ({"title": " "}, {"title": None}, {"cefr_level": "C2"}, {"topic": None}):
        assert client.patch(path, headers=owner, json=payload).status_code == 422
    renamed = client.patch(path, headers=owner, json={"title": "  Practice one  "}).json()
    assert renamed["title"] == "Practice one" and renamed["topic"] == "Travel"
    changed = client.patch(path, headers=owner, json={"topic": "Shopping", "cefr_level": "B2"}).json()
    assert changed["cefr_level"] == "B2"
    prompts = []

    async def reply(messages):
        prompts.append(messages)
        yield "What would you buy?"

    monkeypatch.setattr("app.llm.stream_reply", reply)
    client.post("/chat/stream", headers=owner, json={"request_id": str(uuid4()), "session_id": first["id"], "text": "Hello"})
    assert "Shopping" in prompts[0][0]["content"] and "B2" in prompts[0][0]["content"]


def test_turn_pagination_and_delete_removes_replay_but_keeps_pronunciation(api):
    client, engine = api
    owner = register(client, "delete-talk@example.com")
    user_id = client.get("/me", headers=owner).json()["id"]
    session_id = client.post("/sessions", headers=owner, json={}).json()["id"]
    request_id = uuid4()
    with engine.connect() as connection:
        connection.execute(text("PRAGMA foreign_keys=ON"))
    with Session(engine) as db:
        for i in range(3):
            db.add(DialogueTurn(session_id=session_id, learner_text=f"Learner {i}", tutor_text=f"Tutor {i}"))
        db.commit()
        record_id, _ = requests.claim(db, user_id, request_id, "chat", {"session_id": session_id, "text": "hello"})
        _, token = reserve_turn(db, user_id, session_id, commit=False)
        db.commit()
        store_turn(db, session_id, "hello", "private response", token, record_id, True)
        # Simulate the normal release at the end of the streaming response.
        from app.dialogue import release_turn
        release_turn(db, session_id, token)
        attempt_id = store_attempt(db, user_id, "hello", {"sentence_score": 70, "words": []}, session_id=session_id)
    first = client.get(f"/sessions/{session_id}/turns?limit=2", headers=owner).json()
    assert first["items"][0]["reply"] == "private response"
    second = client.get(f"/sessions/{session_id}/turns?limit=2&before_id={first['next_cursor']}", headers=owner).json()
    assert len(first["items"]) == len(second["items"]) == 2
    assert second["next_cursor"] is None
    assert {row["id"] for row in first["items"]}.isdisjoint(row["id"] for row in second["items"])
    assert client.get(f"/sessions/{session_id}/turns?limit=101", headers=owner).status_code == 422
    assert client.delete(f"/sessions/{session_id}", headers=owner).status_code == 204
    assert client.get(f"/sessions/{session_id}", headers=owner).status_code == 404
    assert client.get(f"/sessions/{session_id}/turns", headers=owner).status_code == 404
    assert client.get("/sessions", headers=owner).json()["items"] == []
    preserved = client.get(f"/attempts/{attempt_id}", headers=owner).json()
    assert preserved["session_id"] is None and preserved["sentence_score"] == 70
    snapshot = client.get(f"/requests/{request_id}", headers=owner).json()
    assert snapshot["events"] == [{"type": "error", "code": "session_deleted", "request_id": str(request_id)}]
    replay = client.post("/chat/stream", headers=owner, json={"request_id": str(request_id), "session_id": session_id, "text": "hello"})
    assert replay.status_code == 404
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(DialogueTurn)) == 0
        assert db.scalar(select(func.count()).select_from(AIRequest)) == 1


def test_busy_session_rejects_delete_or_lesson_edit_and_late_worker_cannot_restore_it(api):
    client, engine = api
    owner = register(client, "busy-talk@example.com")
    user_id = client.get("/me", headers=owner).json()["id"]
    session_id = client.post("/sessions", headers=owner, json={}).json()["id"]
    with Session(engine) as db:
        record_id, _ = requests.claim(db, user_id, uuid4(), "audio", {"session_id": session_id})
        _, token = reserve_turn(db, user_id, session_id, commit=False)
        db.commit()
    assert client.get(f"/sessions/{session_id}", headers=owner).json()["processing"]
    assert client.delete(f"/sessions/{session_id}", headers=owner).status_code == 409
    assert client.patch(f"/sessions/{session_id}", headers=owner, json={"topic": "Changed"}).status_code == 409
    assert client.patch(f"/sessions/{session_id}", headers=owner, json={"title": "Renamed"}).status_code == 200
    with Session(engine) as db:
        db.get(TalkSession, session_id).busy_until = requests.utcnow() - timedelta(seconds=1)
        db.commit()
    assert client.delete(f"/sessions/{session_id}", headers=owner).status_code == 204
    with Session(engine) as db:
        with pytest.raises(HTTPException):
            store_turn(db, session_id, "late", "must not restore", token, record_id)
        with pytest.raises(HTTPException):
            store_attempt(db, user_id, "late", {"sentence_score": 70, "words": []}, session_id=session_id, request_record_id=record_id)
        assert db.scalar(select(func.count()).select_from(Attempt)) == 0
        assert db.scalar(select(func.count()).select_from(DialogueTurn)) == 0
