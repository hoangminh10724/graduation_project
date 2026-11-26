"""Exercise the receiving Talk backend against a running local WordSpeak speech API."""
import argparse
import json
import os
from pathlib import Path
import secrets
import sys
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", type=Path, required=True, help="Receiving branch's backend directory")
    parser.add_argument("--wav", type=Path, required=True, help="Short English speech recording")
    parser.add_argument("--port", type=int, default=8013)
    parser.add_argument("--require-timings", action="store_true", help="Verify the optional Talk timestamp integration patch")
    args = parser.parse_args()
    sys.path.insert(0, str(args.backend.resolve()))
    from app.db import get_db
    from app.main import app
    from app.models import Base

    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)

    def db():
        with Session(engine) as session:
            yield session

    async def tutor_fixture(messages):
        yield "Could you tell me more?"

    payload = args.wav.read_bytes()
    app.dependency_overrides[get_db] = db
    try:
        with patch.dict(os.environ, {"JWT_SECRET": secrets.token_hex(32),
                                     "AI_SERVICE_URL": f"http://127.0.0.1:{args.port}"}), \
             patch("app.llm.stream_reply", tutor_fixture), TestClient(app) as client:
            def register(email):
                token = client.post("/auth/register", json={"email":email,"password":secrets.token_urlsafe(15)}).raise_for_status().json()["access_token"]
                return {"Authorization":"Bearer " + token}

            owner = register("owner@example.test")
            other = register("other@example.test")
            card = client.post("/cards", headers=owner, json={"front":"seat","back":"Is this seat free?"}).raise_for_status().json()
            assert client.get("/cards/due", headers=other).raise_for_status().json() == []
            assert client.get("/cards/due", headers=owner).raise_for_status().json()[0]["id"] == card["id"]
            review = {"card_id":card["id"], "rating":3, "request_id":str(uuid4())}
            first = client.post("/reviews", headers=owner, json=review).raise_for_status().json()
            assert client.post("/reviews", headers=owner, json=review).raise_for_status().json() == first
            session_id = client.post("/sessions", headers=owner, json={"topic":"Everyday conversation"}).raise_for_status().json()["id"]
            events = []
            with client.websocket_connect("/ws/audio") as ws:
                ws.send_bytes(payload)
                assert ws.receive_json() == {"type":"partial","received_bytes":len(payload)}
                ws.send_json({"type":"end","token":owner["Authorization"].split()[1],
                              "session_id":session_id,"media_type":"audio/wav"})
                while True:
                    event = ws.receive_json()
                    events.append(event)
                    if event["type"] in {"final","error"}:
                        break
            assert events[0]["type"] == "transcript" and events[-2]["type"] == "done", events
            assert events[1:-2] and all(e["type"] == "token" for e in events[1:-2]), events
            words = events[0].get("words", [])
            if args.require_timings:
                assert words, "Expected word timings from the receiving backend"
                previous_end = 0.0
                for word in words:
                    assert word["word"].strip() and previous_end <= word["start"] <= word["end"]
                    previous_end = word["end"]
            assert events[-1]["code"] == "assessment_unavailable"
            turns = client.get(f"/sessions/{session_id}/turns", headers=owner).raise_for_status().json()
            assert turns[0]["text"] == events[0]["text"] and turns[0]["reply"] == events[-2]["text"]
            assert client.get(f"/sessions/{session_id}/turns", headers=other).status_code == 404
            assert client.get("/progress", headers=owner).raise_for_status().json()["attempts"] == 0
            print(json.dumps({"talk_events":[e["type"] for e in events], "score_status":events[-1]["code"],
                              "transcript_received":bool(turns[0]["text"]), "saved_turns":len(turns), "timed_words":len(words),
                              "duplicate_review_replayed":True, "user_isolation":True,
                              "database":"in-memory SQLite", "tutor":"test fixture", "speech":"live local endpoint"}))
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()


if __name__ == "__main__":
    main()
