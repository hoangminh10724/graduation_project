import io
import wave
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app import transcription
from app.main import app

client = TestClient(app)


def wav(seconds, rate=8000):
    output = io.BytesIO()
    with wave.open(output, "wb") as recording:
        recording.setparams((2, 2, rate, 0, "NONE", ""))
        recording.writeframes(bytes(int(seconds * rate) * 4))
    return output.getvalue()


def post(payload):
    return client.post("/transcribe", files={"audio": ("turn", payload)})


def test_rejects_invalid_and_oversize_uploads():
    for payload, status in [(b"", 400), (b"unknown", 415),
                            (bytes(transcription.MAX_BYTES + 1), 413)]:
        assert post(payload).status_code == status


def test_converts_stereo_and_rejects_long_decoded_audio(monkeypatch):
    rate = transcription.RATE
    def recognize(samples, **options):
        assert len(samples) == rate
        assert options["word_timestamps"] and options["vad_filter"]
        word = SimpleNamespace(word=" Hello", start=0.1, end=0.8)
        return [SimpleNamespace(text=" Hello", words=[word])], None

    monkeypatch.setattr(transcription, "model", lambda: SimpleNamespace(transcribe=recognize))
    assert post(wav(1)).json() == {"text": "Hello", "words": [{"word": "Hello", "start": 0.1, "end": 0.8}]}
    assert post(wav(31)).status_code == 413


def test_no_speech_and_model_failure(monkeypatch):
    monkeypatch.setattr(transcription, "model", lambda: SimpleNamespace(transcribe=lambda *a, **k: ([], None)))
    assert post(wav(1)).status_code == 422
    def unavailable():
        raise OSError("missing model")
    monkeypatch.setattr(transcription, "model", unavailable)
    assert post(wav(1)).status_code == 503
