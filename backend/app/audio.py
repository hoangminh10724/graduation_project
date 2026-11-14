import asyncio
import json
import logging
from typing import Literal
from time import monotonic
from contextlib import aclosing

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from .auth import DB, user_from_token
from .dialogue import chat_events, reserve_turn, release_turn
from .progress import store_attempt
from .speech import SpeechError, request_audio
from .limits import enforce_limit

router = APIRouter()
logger = logging.getLogger(__name__)
MAX_AUDIO_BYTES = 8 * 1024 * 1024
MAX_CONTROL_BYTES = 24 * 1024


class AudioEnd(BaseModel):
    type: Literal["end"]
    token: str | None = Field(default=None, min_length=1, max_length=4096)
    media_type: Literal["audio/webm", "audio/wav"] = "audio/webm"
    text: str | None = Field(default=None, min_length=1, max_length=5000)
    session_id: int | None = Field(default=None, gt=0)


class AudioAuth(BaseModel):
    type: Literal["auth"]
    token: str = Field(min_length=1, max_length=4096)


def authenticate(db: DB, token: str) -> int:
    try:
        return user_from_token(db, token).id
    finally:
        db.rollback()


def prepare_turn(db: DB, payload: AudioEnd, connection_token: str) -> tuple[int, list[dict[str, str]], str | None]:
    try:
        user_id = authenticate(db, connection_token)
        if payload.token is not None and payload.token != connection_token:
            raise HTTPException(401, "Connection identity cannot change")
        enforce_limit(db, "ai-turn", str(user_id), 20)
        messages, token = reserve_turn(db, user_id, payload.session_id) if payload.session_id else ([], None)
        return user_id, messages, token
    finally:
        db.rollback()


async def complete_audio(ws: WebSocket, db: DB, payload: AudioEnd, audio: bytes, connection_token: str) -> None:
    user_id, messages, token = await run_in_threadpool(prepare_turn, db, payload, connection_token)
    assessment_task = None
    try:
        reference_text = (payload.text.strip() if payload.text else "") or None
        transcript = None
        if reference_text is None:
            result = await request_audio("/transcribe", audio, payload.media_type)
            transcript = result["text"]
        assessment_text = reference_text or transcript
        assessment_task = asyncio.create_task(
            request_audio("/assess", audio, payload.media_type, assessment_text)
        )
        await ws.send_json({
            "type": "transcript", "text": assessment_text,
            "text_source": "reference" if reference_text else "stt",
        })
        if payload.session_id is not None:
            async with aclosing(chat_events(db, payload.session_id, assessment_text, messages, token)) as events:
                async for event in events:
                    await ws.send_json(event)
        try:
            assessment = await assessment_task
        except SpeechError:
            await ws.send_json({"type": "error", "code": "assessment_unavailable"})
            return
        attempt_id = await run_in_threadpool(
            store_attempt, db, user_id, assessment_text, assessment,
            reference_text, transcript, payload.session_id,
        )
        await ws.send_json({
            "type": "final", "text": assessment_text, "assessment": assessment,
            "attempt_id": attempt_id,
        })
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
        await run_in_threadpool(enforce_limit, db, "ws-connect", ws.client.host if ws.client else "unknown", 30)
        first = await asyncio.wait_for(ws.receive(), timeout=10)
        control = first.get("text") or ""
        if len(control.encode()) > MAX_CONTROL_BYTES:
            raise ValueError("Authentication message exceeds size limit")
        auth = AudioAuth.model_validate_json(control)
        await run_in_threadpool(authenticate, db, auth.token)
        await ws.send_json({"type": "authenticated"})
        recording_started = None
        while True:
            remaining = 60 if recording_started is None else min(60, 120 - (monotonic() - recording_started))
            message = await asyncio.wait_for(ws.receive(), timeout=max(0, remaining))
            if message["type"] == "websocket.disconnect":
                return
            chunk = message.get("bytes")
            if chunk is not None:
                if recording_started is None:
                    recording_started = monotonic()
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
                async with asyncio.timeout(180):
                    await complete_audio(ws, db, payload, bytes(buffer), auth.token)
            except HTTPException as exc:
                code = {401: "unauthorized", 404: "session_not_found", 409: "session_busy", 429: "rate_limited"}.get(exc.status_code, "unavailable")
                await ws.send_json({"type": "error", "code": code})
                if exc.status_code == 401:
                    await ws.close(code=1008)
                    return
            except SpeechError:
                await ws.send_json({"type": "error", "code": "speech_unavailable"})
            except SQLAlchemyError:
                await run_in_threadpool(db.rollback)
                logger.exception("Failed to process a Talk audio turn")
                await ws.send_json({"type": "error", "code": "database_unavailable"})
            finally:
                buffer.clear()
                recording_started = None
                await run_in_threadpool(db.rollback)
    except HTTPException as exc:
        await ws.send_json({"type": "error", "code": "rate_limited" if exc.status_code == 429 else "authentication_required"})
        await ws.close(code=1008)
    except (ValidationError, ValueError):
        await ws.send_json({"type": "error", "code": "authentication_required"})
        await ws.close(code=1008)
    except TimeoutError:
        await ws.close(code=1008, reason="Audio connection timed out")
    except WebSocketDisconnect:
        return
    finally:
        await run_in_threadpool(db.rollback)
