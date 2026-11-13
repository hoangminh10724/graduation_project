from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.exc import OperationalError

from app import main
from app.db import get_db
from app.main import app

client = TestClient(app)


def test_health(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    monkeypatch.setattr(main, "get_engine", lambda: engine)
    try:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
    finally:
        engine.dispose()


def test_health_when_database_is_unavailable(monkeypatch):
    engine = create_engine("sqlite://")

    @event.listens_for(engine, "do_connect")
    def fail_to_connect(*_args):
        raise OperationalError(None, None, OSError("database is unavailable"))

    monkeypatch.setattr(main, "get_engine", lambda: engine)
    try:
        response = client.get("/health")
        assert response.status_code == 503
        assert response.json() == {"status": "unavailable"}
    finally:
        engine.dispose()


def test_ws_audio_counts_bytes(monkeypatch):
    monkeypatch.setitem(app.dependency_overrides, get_db, lambda: None)
    with client.websocket_connect("/ws/audio") as ws:
        ws.send_bytes(b"1234")
        assert ws.receive_json()["received_bytes"] == 4
        ws.send_bytes(b"56")
        assert ws.receive_json()["received_bytes"] == 6
