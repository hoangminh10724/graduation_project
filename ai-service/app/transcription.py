"""Local English turn transcription. Word times are ASR estimates in seconds."""
from functools import lru_cache
from io import BytesIO
from itertools import chain
import os
from pathlib import Path
from threading import Lock

from fastapi import APIRouter, File, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

router = APIRouter()
MAX_BYTES = 8 * 1024 * 1024
RATE = 16000
MAX_SECONDS = 30
DEFAULT_MODEL = Path(__file__).resolve().parents[2] / "data/models/native-preparation/whisper-small.en"
inference_lock = Lock()


def decode(payload):
    if payload.startswith(b"RIFF") and payload[8:12] == b"WAVE":
        container_format = "wav"
    elif payload.startswith(bytes.fromhex("1a45dfa3")):
        container_format = "matroska"
    elif not payload:
        raise HTTPException(400, "Empty recording.")
    else:
        raise HTTPException(415, "Send a WAV or WebM recording.")

    try:
        import av
        import numpy as np
    except (ImportError, OSError) as exc:
        raise HTTPException(503, "The audio decoder is unavailable.") from exc

    # Stop decoding at the sample limit even when container metadata is missing.
    chunks = []
    total = 0
    try:
        with av.open(BytesIO(payload), format=container_format) as container:
            if not container.streams.audio:
                raise HTTPException(400, "No audio stream.")
            resampler = av.AudioResampler(format="s16", layout="mono", rate=RATE)
            for frame in chain(container.decode(audio=0), [None]):
                if frame is not None:
                    frame.pts = None
                for out in resampler.resample(frame):
                    total += out.samples
                    if total > RATE * MAX_SECONDS:
                        raise HTTPException(413, "Maximum recording length is 30 seconds.")
                    chunks.append(out.to_ndarray().reshape(-1))
    except (av.FFmpegError, ValueError, EOFError) as exc:
        raise HTTPException(400, "Could not decode this recording.") from exc
    if not total:
        raise HTTPException(400, "No audio samples.")
    return np.concatenate(chunks).astype(np.float32) / 32768.0


@lru_cache(maxsize=1)
def model():
    from faster_whisper import WhisperModel

    return WhisperModel(os.environ.get("WORDSPEAK_WHISPER_MODEL", str(DEFAULT_MODEL)),
                        device="cpu", compute_type="int8", cpu_threads=4,
                        local_files_only=True)


def recognize(payload):
    samples = decode(payload)
    try:
        with inference_lock:
            segments, _ = model().transcribe(samples, language="en", beam_size=5,
                                             vad_filter=True, word_timestamps=True,
                                             condition_on_previous_text=False)
            segments = list(segments)
    except (ImportError, OSError, RuntimeError, ValueError) as exc:
        raise HTTPException(503, "Local English transcription is unavailable.") from exc
    text = " ".join(s.text.strip() for s in segments if s.text.strip())
    if not text or len(text) > 5000:
        raise HTTPException(422, "No usable English transcript. Try a clearer recording.")
    duration = len(samples) / RATE
    words = [{"word": w.word.strip(), "start": min(duration, max(0, w.start)),
              "end": min(duration, max(0, w.start, w.end))}
             for s in segments for w in (s.words or []) if w.word.strip()]
    return {"text": text, "words": words}


@router.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    try:
        payload = await audio.read(MAX_BYTES + 1)
    finally:
        await audio.close()
    if len(payload) > MAX_BYTES:
        raise HTTPException(413, "Maximum upload size is 8 MiB.")
    return await run_in_threadpool(recognize, payload)
