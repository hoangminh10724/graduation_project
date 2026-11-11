from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_ws_audio_counts_bytes():
    with client.websocket_connect("/ws/audio") as ws:
        ws.send_bytes(b"1234")
        assert ws.receive_json()["received_bytes"] == 4
        ws.send_bytes(b"56")
        assert ws.receive_json()["received_bytes"] == 6
