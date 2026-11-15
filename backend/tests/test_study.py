from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session

from app.cards import ReviewCreate, review_card, utc_now
from app.models import Base, Card, Review, StudyItem, StudySession, User
from app.study import StudyCreate, create_study
from test_cards import api, register


def add_card(client, headers, front="hello", deck_id=None):
    return client.post("/cards", headers=headers, json={"front": front, "back": "translation", "deck_id": deck_id}).json()


def test_study_resume_reviews_idempotency_and_completion(api):
    client, engine = api
    owner = register(client, "study@example.com")
    first, second = [add_card(client, owner, word) for word in ("one", "two")]
    start = {"request_id": str(uuid4()), "limit": 2}
    response = client.post("/study-sessions", headers=owner, json=start)
    assert response.status_code == 201
    study = response.json()
    study_id = study["id"]
    assert study["status"] == "active" and study["selected"] == study["remaining"] == 2
    assert [card["id"] for card in study["queue"]] == [first["id"], second["id"]]
    assert client.post("/study-sessions", headers=owner, json=start).json()["id"] == study_id
    assert client.post("/study-sessions", headers=owner, json={**start, "limit": 1}).status_code == 409
    busy = client.post("/study-sessions", headers=owner, json={"request_id": str(uuid4())})
    assert busy.status_code == 409 and busy.json()["detail"]["study_session_id"] == study_id
    payload = {"request_id": str(uuid4()), "study_session_id": study_id, "card_id": first["id"], "rating": 1}
    reviewed = client.post("/reviews", headers=owner, json=payload)
    assert reviewed.status_code == 200 and reviewed.json()["interval_seconds"] == 600
    assert client.post("/reviews", headers=owner, json=payload).json() == reviewed.json()
    assert client.post("/reviews", headers=owner, json={**payload, "study_session_id": None}).status_code == 409
    assert client.post("/reviews", headers=owner, json={**payload, "request_id": str(uuid4())}).status_code == 409
    resumed = client.get(f"/study-sessions/{study_id}", headers=owner).json()
    assert resumed["reviewed"] == resumed["remaining"] == 1
    assert resumed["ratings"]["again"] == 1 and resumed["queue"][0]["id"] == second["id"]
    last = {**payload, "request_id": str(uuid4()), "card_id": second["id"], "rating": 3}
    assert client.post("/reviews", headers=owner, json=last).status_code == 200
    finished = client.get(f"/study-sessions/{study_id}", headers=owner).json()
    assert finished["status"] == "completed" and finished["queue"] == []
    assert finished["reviewed"] == 2 and finished["remaining"] == finished["skipped"] == 0
    assert finished["ratings"] == {"again": 1, "hard": 0, "good": 1, "easy": 0}
    assert finished["finished_at"] is not None
    assert client.post("/reviews", headers=owner, json=last).status_code == 200
    assert client.post(f"/study-sessions/{study_id}/finish", headers=owner).json() == finished
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(Review)) == 2
        assert db.scalar(select(func.count()).select_from(StudySession)) == 1


def test_study_scope_ownership_filters_and_early_finish(api):
    client, engine = api
    owner = register(client, "owner-study@example.com")
    other = register(client, "other-study@example.com")
    deck_id = client.post("/decks", headers=owner, json={"name": "Travel"}).json()["id"]
    due = add_card(client, owner, "due", deck_id)
    future = add_card(client, owner, "future", deck_id)
    suspended = add_card(client, owner, "suspended", deck_id)
    unrelated = add_card(client, owner, "unrelated")
    with Session(engine) as db:
        db.get(Card, future["id"]).due = utc_now() + timedelta(days=1)
        db.get(Card, suspended["id"]).suspended = True
        db.commit()
    assert client.post("/study-sessions", headers=other, json={"request_id": str(uuid4()), "deck_id": deck_id}).status_code == 404
    for limit in (0, 101, True):
        assert client.post("/study-sessions", headers=owner, json={"request_id": str(uuid4()), "limit": limit}).status_code == 422
    study = client.post("/study-sessions", headers=owner, json={"request_id": str(uuid4()), "deck_id": deck_id}).json()
    study_id = study["id"]
    assert [card["id"] for card in study["queue"]] == [due["id"]]
    assert client.get(f"/study-sessions/{study_id}", headers=other).status_code == 404
    assert client.post(f"/study-sessions/{study_id}/finish", headers=other).status_code == 404
    assert client.get("/study-sessions", headers=other).json()["items"] == []
    assert client.post("/reviews", headers=owner, json={
        "request_id": str(uuid4()), "study_session_id": study_id, "card_id": unrelated["id"], "rating": 3,
    }).status_code == 409
    finished = client.post(f"/study-sessions/{study_id}/finish", headers=owner).json()
    assert finished["status"] == "completed" and finished["skipped_reasons"] == {"ended_early": 1}
    assert client.get(f"/cards/{due['id']}", headers=owner).json()["due"] == due["due"]
    assert client.post("/reviews", headers=owner, json={
        "request_id": str(uuid4()), "study_session_id": study_id, "card_id": due["id"], "rating": 3,
    }).status_code == 409
    next_study = client.post("/study-sessions", headers=owner, json={"request_id": str(uuid4()), "deck_id": deck_id}).json()
    page = client.get("/study-sessions?limit=1", headers=owner).json()
    assert page["items"][0]["id"] == next_study["id"]
    previous = client.get(f"/study-sessions?before_id={page['next_cursor']}&limit=1", headers=owner).json()
    assert previous["items"][0]["id"] == study_id and previous["next_cursor"] is None
    assert len(client.get("/study-sessions?status=completed", headers=owner).json()["items"]) == 1


def test_study_handles_deleted_suspended_and_externally_reviewed_cards(api):
    client, engine = api
    owner = register(client, "stale-study@example.com")
    cards = [add_card(client, owner, str(i)) for i in range(3)]
    study_id = client.post("/study-sessions", headers=owner, json={"request_id": str(uuid4())}).json()["id"]
    client.delete(f"/cards/{cards[0]['id']}", headers=owner)
    client.patch(f"/cards/{cards[1]['id']}", headers=owner, json={"suspended": True})
    client.post("/reviews", headers=owner, json={"request_id": str(uuid4()), "card_id": cards[2]["id"], "rating": 3})
    result = client.get(f"/study-sessions/{study_id}", headers=owner).json()
    assert result["status"] == "completed" and result["skipped"] == 3 and result["reviewed"] == 0
    assert result["skipped_reasons"] == {"card_deleted": 1, "card_suspended": 1, "schedule_changed": 1}
    assert result["queue"] == []
    empty = client.post("/study-sessions", headers=owner, json={"request_id": str(uuid4())}).json()
    assert empty["selected"] == 0 and empty["status"] == "completed"


def test_study_summary_survives_card_and_deck_deletion(api):
    client, engine = api
    owner = register(client, "preserve-study@example.com")
    with engine.connect() as connection:
        connection.execute(text("PRAGMA foreign_keys=ON"))
    deck_id = client.post("/decks", headers=owner, json={"name": "Travel"}).json()["id"]
    card = add_card(client, owner, deck_id=deck_id)
    start = {"request_id": str(uuid4()), "deck_id": deck_id}
    study_id = client.post("/study-sessions", headers=owner, json=start).json()["id"]
    assert client.post("/reviews", headers=owner, json={
        "request_id": str(uuid4()), "study_session_id": study_id, "card_id": card["id"], "rating": 4,
    }).status_code == 200
    assert client.delete(f"/decks/{deck_id}", headers=owner).status_code == 204
    assert client.delete(f"/cards/{card['id']}", headers=owner).status_code == 204
    result = client.get(f"/study-sessions/{study_id}", headers=owner).json()
    assert result["reviewed"] == 1 and result["ratings"]["easy"] == 1 and result["deck_id"] is None
    assert client.post("/study-sessions", headers=owner, json=start).json()["id"] == study_id
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(Review)) == 0
        assert db.scalar(select(StudyItem.rating)) == 4


@pytest.mark.parametrize("same_request", [True, False])
def test_concurrent_starts_and_ratings_do_not_duplicate_study_or_review(tmp_path, same_request):
    engine = create_engine(f"sqlite:///{tmp_path / 'study.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(User(id=1, email="concurrent-study@example.test", password_hash="unused"))
        db.add(Card(id=1, user_id=1, front="hello", back="translation", due=utc_now()))
        db.commit()
    request_id = uuid4()
    start_barrier = Barrier(2)

    def start_worker(_):
        with Session(engine) as db:
            user = db.get(User, 1)
            start_barrier.wait(timeout=5)
            try:
                result = create_study(StudyCreate(request_id=request_id if same_request else uuid4()), user, db)
                return 201, result.id
            except HTTPException as error:
                return error.status_code, None

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(start_worker, range(2)))
        assert sorted(status for status, _ in results) == ([201, 201] if same_request else [201, 409])
        with Session(engine) as db:
            assert db.scalar(select(func.count()).select_from(StudySession)) == 1
            study_id = db.scalar(select(StudySession.id))
        review_barrier = Barrier(2)

        def review_worker(_):
            with Session(engine) as db:
                user = db.get(User, 1)
                review_barrier.wait(timeout=5)
                try:
                    review_card(ReviewCreate(request_id=uuid4(), card_id=1, rating=3, study_session_id=study_id), user, db)
                    return 200
                except HTTPException as error:
                    return error.status_code

        with ThreadPoolExecutor(max_workers=2) as pool:
            assert sorted(pool.map(review_worker, range(2))) == [200, 409]
        with Session(engine) as db:
            assert db.scalar(select(func.count()).select_from(Review)) == 1
            assert db.get(StudySession, study_id).status == "completed"
            assert db.get(Card, 1).stability == pytest.approx(3.173)
    finally:
        engine.dispose()
