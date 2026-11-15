from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import dashboard
from app.models import Attempt, Card, DialogueTurn, Review, Session as TalkSession, User
from test_cards import api, register


def test_dashboard_counts_owned_outcomes_and_today_outside_range(api, monkeypatch):
    client, engine = api
    owner = register(client, "dashboard@example.test")
    other = register(client, "other@example.test")

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            value = datetime(2026, 11, 15, 18, tzinfo=timezone.utc)
            return value.astimezone(tz) if tz else value.replace(tzinfo=None)

    monkeypatch.setattr(dashboard, "datetime", Clock)
    with Session(engine) as db:
        user = db.scalar(select(User).where(User.email == "dashboard@example.test"))
        outsider = db.scalar(select(User).where(User.email == "other@example.test"))
        user.daily_goal = 3
        for person in (user, outsider):
            talk = TalkSession(user_id=person.id)
            card = Card(user_id=person.id, front="hello", back="hi", due=datetime(2026, 11, 15))
            db.add_all([talk, card])
            db.flush()
            db.add_all([
                Attempt(user_id=person.id, text="hello", sentence_score=70, created_at=datetime(2026, 11, 15, 17)),
                DialogueTurn(session_id=talk.id, learner_text="hello", tutor_text="hi", completed_at=datetime(2026, 11, 15, 17)),
                DialogueTurn(session_id=talk.id, learner_text="old", tutor_text="hi"),
                Review(card_id=card.id, rating=3, reviewed_at=datetime(2026, 11, 15, 17)),
                Attempt(user_id=person.id, text="yesterday", sentence_score=60, created_at=datetime(2026, 11, 15, 16, 59, 59)),
                Card(user_id=person.id, front="suspended", back="hi", suspended=True, due=datetime(2026, 11, 14)),
                Card(user_id=person.id, front="future", back="hi", due=datetime(2026, 12, 1)),
            ])
        db.commit()
    result = client.get("/dashboard", headers=owner).json()
    assert len(result["daily"]) == 30
    assert result["date_to"] == "2026-11-16"
    assert result["totals"] == {"pronunciation": 2, "talk": 1, "reviews": 1, "total": 4}
    assert result["today"]["completed"] == 3 and result["today"]["achieved"]
    assert result["today"]["remaining"] == 0
    assert result["due_cards"] == 1 and result["undated_talk_turns"] == 1
    assert result["active_study_session_id"] is None
    assert result["daily"][-2]["total"] == 1 and result["daily"][-1]["total"] == 3
    selected = client.get("/dashboard", headers=owner, params={"date_from": "2020-01-01", "date_to": "2020-01-02"}).json()
    assert selected["totals"]["total"] == 0 and len(selected["daily"]) == 2
    assert selected["today"] == result["today"]
    assert client.get("/dashboard", headers=other).json()["totals"] == result["totals"]
    assert client.get("/dashboard").status_code == 401
    for params in ({"date_from": "2026-01-01"}, {"timezone_name": "unknown"},
                   {"date_from": "0001-01-01", "date_to": "0001-01-01"},
                   {"date_from": "2020-01-01", "date_to": "2026-01-01"},
                   {"date_from": "2026-01-02", "date_to": "2026-01-01"}):
        assert client.get("/dashboard", headers=owner, params=params).status_code == 422


def test_dashboard_replays_do_not_inflate_goal_and_deletion_updates_counts(api, monkeypatch):
    client, engine = api
    owner = register(client, "replay-dashboard@example.test")
    client.patch("/me", headers=owner, json={"daily_goal": 1})
    talk = client.post("/sessions", headers=owner, json={}).json()

    async def reply(messages):
        yield "What did you learn?"

    monkeypatch.setattr("app.llm.stream_reply", reply)
    payload = {"request_id": str(uuid4()), "session_id": talk["id"], "text": "Hello"}
    for _ in range(2):
        assert "done" in client.post("/chat/stream", headers=owner, json=payload).text
    with Session(engine) as db:
        turn = db.scalar(select(DialogueTurn))
        assert turn.completed_at is not None
    card = client.post("/cards", headers=owner, json={"front": "a", "back": "b"}).json()
    study = client.post("/study-sessions", headers=owner, json={"request_id": str(uuid4())}).json()
    assert client.get("/dashboard", headers=owner).json()["active_study_session_id"] == study["id"]
    review = {"request_id": str(uuid4()), "card_id": card["id"], "rating": 3}
    for _ in range(2):
        assert client.post("/reviews", headers=owner, json=review).status_code == 200
    result = client.get("/dashboard", headers=owner).json()
    assert result["today"]["completed"] == 2 and result["today"]["remaining"] == 0
    assert result["totals"]["total"] == 2 and result["undated_talk_turns"] == 0
    assert client.delete(f"/sessions/{talk['id']}", headers=owner).status_code == 204
    assert client.delete(f"/cards/{card['id']}", headers=owner).status_code == 204
    assert client.get("/dashboard", headers=owner).json()["today"]["completed"] == 0


@pytest.mark.parametrize("day,hours", [(date(2026, 3, 8), 23), (date(2026, 11, 1), 25)])
def test_dashboard_window_uses_local_calendar(day, hours):
    from zoneinfo import ZoneInfo
    start, end = dashboard.utc_window(day, day, ZoneInfo("America/New_York"))
    assert end - start == timedelta(hours=hours)
