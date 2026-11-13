import asyncio
import json
import logging
from typing import Literal

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from .auth import DB, user_from_token
from .dialogue import chat_events, reserve_turn, release_turn
from .progress import store_attempt
from .speech import SpeechError, request_audio

router = APIRouter()
logger = logging.getLogger(__name__)
MAX_AUDIO_BYTES = 8 * 1024 * 1024
MAX_CONTROL_BYTES = 24 * 1024


class AudioEnd(BaseModel):
    type: Literal["end"]
    token: str = Field(min_length=1, max_length=4096)
    media_type: Literal["audio/webm", "audio/wav"] = "audio/webm"
    text: str | None = Field(default=None, min_length=1, max_length=5000)
    session_id: int | None = Field(default=None, gt=0)


def prepare_turn(db: DB, payload: AudioEnd) -> tuple[int, list[dict[str, str]], str | None]:
    user_id = user_from_token(db, payload.token).id
    messages, token = reserve_turn(db, user_id, payload.session_id) if payload.session_id else ([], None)
    db.rollback()
    return user_id, messages, token


async def complete_audio(ws: WebSocket, db: DB, payload: AudioEnd, audio: bytes) -> None:
    user_id, messages, token = await run_in_threadpool(prepare_turn, db, payload)
    assessment_task = None
    try:
        transcript = payload.text.strip() if payload.text else ""
        if not transcript:
            result = await request_audio("/transcribe", audio, payload.media_type)
            transcript = result["text"]
        assessment_task = asyncio.create_task(
            request_audio("/assess", audio, payload.media_type, transcript)
        )
        await ws.send_json({"type": "transcript", "text": transcript})
        if payload.session_id is not None:
            async for event in chat_events(db, payload.session_id, transcript, messages):
                await ws.send_json(event)
        try:
            assessment = await assessment_task
        except SpeechError:
            await ws.send_json({"type": "error", "code": "assessment_unavailable"})
            return
        await run_in_threadpool(store_attempt, db, user_id, transcript, assessment)
        await ws.send_json({"type": "final", "text": transcript, "assessment": assessment})
        hints = assessment.get("hints", [])
        errors = assessment.get("errors", [])
        if hints or errors:
            await ws.send_json({"type": "coaching", "hints": hints, "errors": errors})
    finally:
        if assessment_task is not None:
            assessment_task.cancel()
            await asyncio.gather(assessment_task, return_exceptions=True)
        if token is not None:
            await run_in_threadpool(release_turn, db, payload.session_id, token)


@router.websocket("/ws/audio")
async def ws_audio(ws: WebSocket, db: DB):
    origins = ws.app.state.cors_origins
    origin = ws.headers.get("origin")
    if origin and origin not in origins and "*" not in origins:
        await ws.close(code=1008)
        return
    await ws.accept()
    buffer = bytearray()
    try:
        while True:
            message = await asyncio.wait_for(ws.receive(), timeout=60)
            if message["type"] == "websocket.disconnect":
                return
            chunk = message.get("bytes")
            if chunk is not None:
                if len(buffer) + len(chunk) > MAX_AUDIO_BYTES:
                    await ws.send_json({"type": "error", "code": "audio_too_large"})
                    await ws.close(code=1009)
                    return
                buffer.extend(chunk)
                await ws.send_json({"type": "partial", "received_bytes": len(buffer)})
                continue

            try:
                control = message.get("text") or ""
                if len(control.encode()) > MAX_CONTROL_BYTES:
                    raise ValueError("Audio control message exceeds its size limit")
                payload = AudioEnd.model_validate(json.loads(control))
                if not buffer:
                    await ws.send_json({"type": "error", "code": "empty_audio"})
                    continue
            except (ValidationError, ValueError):
                buffer.clear()
                await ws.send_json({"type": "error", "code": "invalid_end_message"})
                continue
            try:
                await complete_audio(ws, db, payload, bytes(buffer))
            except HTTPException as exc:
                code = {401: "unauthorized", 404: "session_not_found", 409: "session_busy"}.get(exc.status_code, "unavailable")
                await ws.send_json({"type": "error", "code": code})
            except SpeechError:
                await ws.send_json({"type": "error", "code": "speech_unavailable"})
            except SQLAlchemyError:
                await run_in_threadpool(db.rollback)
                logger.exception("Failed to process a Talk audio turn")
                await ws.send_json({"type": "error", "code": "database_unavailable"})
            finally:
                buffer.clear()
    except TimeoutError:
        await ws.close(code=1008, reason="Audio connection timed out")
    except WebSocketDisconnect:
        return
