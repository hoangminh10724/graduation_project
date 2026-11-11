from fastapi.testclient import TestClient

from app.gop import normalize_gop
from app.main import app

client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_normalize_gop_bounds():
    assert normalize_gop(0.0) == 100.0
    assert normalize_gop(-5.0) == 0.0
    assert normalize_gop(-10.0) == 0.0
    assert normalize_gop(-2.5) == 50.0


def test_assess_shape():
    r = client.post(
        "/assess",
        files={"audio": ("a.wav", b"RIFF", "audio/wav")},
        data={"text": "hello world"},
    )
    body = r.json()
    assert r.status_code == 200
    assert len(body["words"]) == 2
    assert 0 <= body["sentence_score"] <= 100
