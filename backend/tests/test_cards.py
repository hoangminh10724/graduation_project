import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import get_db
from app.main import app
from app.models import Base, Review


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
    payload = {"card_id": card["id"], "rating": 3}
    assert client.post("/reviews", headers=other, json=payload).status_code == 404
    assert client.post("/reviews", headers=owner, json={**payload, "rating": 5}).status_code == 422

    response = client.post("/reviews", headers=owner, json=payload)
    assert response.status_code == 200
    assert response.json()["interval_days"] == 3
    assert response.json()["card"]["stability"] == pytest.approx(3.173)
    assert client.get("/cards/due", headers=owner).json() == []

    response = client.post("/reviews", headers=owner, json={**payload, "rating": 1})
    assert response.status_code == 200
    assert response.json()["card"]["stability"] < 3.173
    with Session(engine) as db:
        assert list(db.scalars(select(Review.rating).order_by(Review.id))) == [3, 1]


def test_login_and_duplicate_registration(api):
    client, _ = api
    register(client, "user@example.com")
    credentials = {"email": "USER@example.com", "password": "test-pass"}
    assert client.post("/auth/register", json=credentials).status_code == 409
    assert client.post("/auth/login", json=credentials).status_code == 200
    assert client.post("/auth/login", json={**credentials, "password": "wrong-pass"}).status_code == 401
