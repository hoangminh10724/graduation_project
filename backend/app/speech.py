import os
from typing import Annotated

import httpx
from pydantic import BaseModel, Field, StringConstraints


class SpeechError(RuntimeError):
    pass


class Phoneme(BaseModel):
    ipa: str
    score: float = Field(ge=0, le=100)
    start: float
    end: float


class Word(BaseModel):
    word: str
    score: float = Field(ge=0, le=100)
    phonemes: list[Phoneme]


class Assessment(BaseModel):
    sentence_score: float = Field(ge=0, le=100)
    words: list[Word]
    errors: list[dict] = Field(default_factory=list)
    hints: list[str] = Field(default_factory=list)


class Transcript(BaseModel):
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)]


async def request_audio(
    path: str, audio: bytes, media_type: str, text: str | None = None
) -> dict:
    filename = "speech.wav" if media_type == "audio/wav" else "speech.webm"
    base_url = os.getenv("AI_SERVICE_URL", "http://localhost:8001")
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30, connect=5)) as client:
            response = await client.post(
                f"{base_url.rstrip('/')}{path}",
                files={"audio": (filename, audio, media_type)},
                data={"text": text} if text is not None else None,
            )
            response.raise_for_status()
            if path == "/transcribe":
                return Transcript.model_validate(response.json()).model_dump()
            return Assessment.model_validate(response.json()).model_dump()
    except (httpx.HTTPError, ValueError) as exc:
        raise SpeechError(f"Speech service request failed: {path}") from exc
