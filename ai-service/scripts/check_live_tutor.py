"""Collect live tutor replies to authored conversation scenarios for teaching review."""
import argparse
import json
import os
from pathlib import Path
import secrets
import sys
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


SCENARIOS = [
    ("A2", "Finding a seat", ["Is this seat free?", "I meant the seat near the window."],
     "Does the tutor respond to the seat request and follow the clarification about the window?"),
    ("B1", "Taking a rain check", ["Can I take a rain check on dinner?", "Friday works for me after six."],
     "Does the tutor understand the idiom and use the new availability to continue planning?"),
    ("B2", "Clarifying a booking", ["I said fifteen guests, but the booking shows fifty.",
     "Which sound did I pronounce wrong? You only have my typed message."],
     "Does the tutor address the booking mix-up and avoid claiming it heard a specific pronunciation error?"),
]


def collect(client, headers):
    cases = []
    for level, topic, lines, question in SCENARIOS:
        session = client.post("/sessions", headers=headers, json={"cefr_level": level, "topic": topic})
        session_id = session.raise_for_status().json()["id"]
        turns = []
        for line in lines:
            response = client.post("/chat/stream", headers=headers, json={"session_id": session_id, "text": line})
            response.raise_for_status()
            events = [json.loads(row[5:]) for row in response.text.splitlines() if row.startswith("data:")]
            done = [e["text"] for e in events if e["type"] == "done"]
            if len(done) != 1 or not done[0].strip():
                code = next((e.get("code") for e in events if e["type"] == "error"), "incomplete_reply")
                raise RuntimeError(f"{topic}: {code}")
            turns.append({"text": line, "reply": done[0]})
        saved = client.get(f"/sessions/{session_id}/turns", headers=headers).raise_for_status().json()
        if turns != [{k:t[k] for k in ("text","reply")} for t in saved]:
            raise RuntimeError("Stored conversation differs from the replies delivered.")
        cases.append({"level": level, "topic": topic, "turns": turns, "review_question": question})
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    if args.report.exists():
        parser.error("Choose a new report path.")
    sys.path.insert(0, str(args.backend.resolve()))
    from app.main import app
    from app.models import Base
    from app.db import get_db
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    def db():
        with Session(engine) as session:
            yield session
    try:
        with patch.dict(app.dependency_overrides, {get_db: db}), patch.dict(os.environ, {"JWT_SECRET": secrets.token_hex(32)}), TestClient(app) as client:
            credentials = {"email": "review@example.test", "password": secrets.token_urlsafe(24)}
            token = client.post("/auth/register", json=credentials).raise_for_status().json()["access_token"]
            cases = collect(client, {"Authorization": "Bearer " + token})
        report = {"model": os.getenv("LLM_MODEL", "qwen2.5:3b"), "teacher_review": "pending", "cases": cases}
        with args.report.open("x", encoding="utf-8") as output:
            json.dump(report, output, indent=2, ensure_ascii=False)
        print(f"Collected {sum(len(c['turns']) for c in cases)} turns for review.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
