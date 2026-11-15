from uuid import uuid4
from sqlalchemy.orm import Session

from app.models import Attempt
from test_cards import api, register


def record(client, authorization, text=None, session_id=None):
    with client.websocket_connect("/ws/audio") as socket:
        socket.send_json({"type": "auth", "token": authorization["Authorization"].split()[1]})
        assert socket.receive_json()["type"] == "authenticated"
        socket.send_bytes(b"audio")
        assert socket.receive_json()["type"] == "partial"
        payload = {"type": "end", "request_id": str(uuid4())}
        if text is not None:
            payload["text"] = text
        if session_id is not None:
            payload["session_id"] = session_id
        socket.send_json(payload)
        events = []
        while not events or events[-1]["type"] != "final":
            events.append(socket.receive_json())
        return events


def test_audio_history_provenance_pagination_and_ownership(api, monkeypatch):
    client, _ = api
    owner = register(client, "history@example.com")
    other = register(client, "other@example.com")
    speech_calls = []

    async def speech(path, audio, media_type, text=None):
        speech_calls.append(path)
        if path == "/transcribe":
            return {"text": "I think so."}
        return {"sentence_score": 72, "words": [], "errors": [{"ipa": "θ"}], "hints": ["Try again."]}

    async def llm(messages):
        yield "What do you think?"

    monkeypatch.setattr("app.audio.request_audio", speech)
    monkeypatch.setattr("app.llm.stream_reply", llm)
    session_id = client.post("/sessions", headers=owner, json={}).json()["id"]
    first = record(client, owner, session_id=session_id)
    first_id = first[-1]["attempt_id"]
    assert first[0]["text_source"] == "stt"
    detail = client.get(f"/attempts/{first_id}", headers=owner).json()
    assert detail["transcript"] == detail["assessment_text"] == "I think so."
    assert detail["reference_text"] is None
    assert detail["session_id"] == session_id
    assert detail["assessment"]["errors"] == [{"ipa": "θ"}]
    assert detail["created_at"].endswith("Z")
    second = record(client, owner, text="  100% ready  ")
    second_id = second[-1]["attempt_id"]
    assert second[0]["text_source"] == "reference"
    detail = client.get(f"/attempts/{second_id}", headers=owner).json()
    assert detail["reference_text"] == detail["assessment_text"] == "100% ready"
    assert detail["transcript"] is None and detail["session_id"] is None
    assert speech_calls == ["/transcribe", "/assess", "/assess"]

    page = client.get("/attempts?limit=1", headers=owner).json()
    assert page["next_cursor"] == second_id
    assert [item["id"] for item in page["items"]] == [second_id]
    assert "assessment" not in page["items"][0]
    # New records between requests do not repeat items already paged through.
    record(client, owner, text="another sentence")
    next_page = client.get(f"/attempts?limit=1&before_id={page['next_cursor']}", headers=owner).json()
    assert [item["id"] for item in next_page["items"]] == [first_id]
    assert next_page["next_cursor"] is None
    matches = client.get("/attempts", headers=owner, params={"q": "%"}).json()
    assert [item["id"] for item in matches["items"]] == [second_id]
    assert [item["id"] for item in client.get(f"/attempts?session_id={session_id}", headers=owner).json()["items"]] == [first_id]
    assert client.get("/attempts", headers=other).json() == {"items": [], "next_cursor": None}
    assert client.get(f"/attempts/{first_id}", headers=other).status_code == 404
    assert client.get(f"/attempts?session_id={session_id}", headers=other).status_code == 404
    assert client.get("/attempts").status_code == 401
    for query in ("limit=0", "limit=101", "before_id=0", "session_id=-1"):
        assert client.get(f"/attempts?{query}", headers=owner).status_code == 422


def test_legacy_attempt_without_provenance_remains_readable(api):
    client, engine = api
    owner = register(client, "legacy@example.com")
    user_id = client.get("/me", headers=owner).json()["id"]
    with Session(engine) as db:
        row = Attempt(user_id=user_id, text="legacy sentence", sentence_score=70, detail_json="{}")
        db.add(row)
        db.flush()
        attempt_id = row.id
        db.commit()
    detail = client.get(f"/attempts/{attempt_id}", headers=owner)
    assert detail.status_code == 200
    assert detail.json()["assessment_text"] == "legacy sentence"
    assert detail.json()["assessment"] is None
    assert detail.json()["reference_text"] is None
    assert detail.json()["transcript"] is None
