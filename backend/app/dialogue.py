import json
import logging
import asyncio
from contextlib import aclosing
from collections.abc import AsyncIterator
from time import perf_counter
from typing import Annotated, Literal
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from anyio import CancelScope
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, StringConstraints
from sqlalchemy import select, update, or_
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from . import llm, requests
from .auth import CurrentUser, DB
from .models import DialogueTurn, Session
from .prompts import coaching_prompt
from .limits import enforce_limit

router = APIRouter()
logger = logging.getLogger(__name__)
LearnerText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)]


class SessionCreate(BaseModel):
    topic: str = Field(default="", max_length=120)
    cefr_level: Literal["A2", "B1", "B2"] | None = None


class SessionView(SessionCreate):
    id: int
    cefr_level: str


class ChatRequest(BaseModel):
    request_id: UUID
    session_id: int = Field(gt=0)
    text: LearnerText


@router.post("/sessions", status_code=201)
def create_session(payload: SessionCreate, user: CurrentUser, db: DB) -> SessionView:
    enforce_limit(db, "sessions", str(user.id), 20)
    level = payload.cefr_level or user.cefr_level
    session = Session(user_id=user.id, topic=payload.topic, cefr_level=level)
    db.add(session)
    db.flush()
    result = SessionView(id=session.id, topic=payload.topic, cefr_level=level)
    db.commit()
    return result


def dialogue_context(db: DB, user_id: int, session_id: int) -> list[dict[str, str]]:
    session = db.scalar(select(Session).where(Session.id == session_id, Session.user_id == user_id))
    if session is None:
        raise HTTPException(404, "Session not found")
    recent = list(db.scalars(
        select(DialogueTurn).where(DialogueTurn.session_id == session_id)
        .order_by(DialogueTurn.id.desc()).limit(6)
    ))
    messages = [{"role": "system", "content": coaching_prompt(session.cefr_level, session.topic)}]
    for turn in reversed(recent):
        messages.extend([
            {"role": "user", "content": turn.learner_text},
            {"role": "assistant", "content": turn.tutor_text},
        ])
    return messages


@router.get("/sessions")
def list_sessions(user: CurrentUser, db: DB) -> list[SessionView]:
    return [
        SessionView(id=s.id, topic=s.topic, cefr_level=s.cefr_level)
        for s in db.scalars(select(Session).where(Session.user_id == user.id).order_by(Session.id.desc()))
    ]


@router.get("/sessions/{session_id}/turns")
def list_turns(session_id: int, user: CurrentUser, db: DB) -> list[dict]:
    dialogue_context(db, user.id, session_id)
    return [
        {"id": t.id, "text": t.learner_text, "reply": t.tutor_text}
        for t in db.scalars(select(DialogueTurn).where(
            DialogueTurn.session_id == session_id
        ).order_by(DialogueTurn.id))
    ]


def reserve_turn(db: DB, user_id: int, session_id: int, *, commit: bool = True) -> tuple[list[dict[str, str]], str]:
    token = str(uuid4())
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    result = db.execute(update(Session).where(
        Session.id == session_id, Session.user_id == user_id,
        or_(Session.busy_until.is_(None), Session.busy_until < now),
    ).values(busy_until=now + timedelta(minutes=5), turn_token=token))
    if result.rowcount != 1:
        db.rollback()
        dialogue_context(db, user_id, session_id)
        raise HTTPException(409, "Session is processing another turn")
    if commit:
        db.commit()
    try:
        messages = dialogue_context(db, user_id, session_id)
        if commit:
            db.rollback()
        return messages, token
    except Exception:
        if commit:
            release_turn(db, session_id, token)
        else:
            db.rollback()
        raise


def release_turn(db: DB, session_id: int, token: str) -> None:
    db.rollback()
    db.execute(update(Session).where(
        Session.id == session_id, Session.turn_token == token
    ).values(busy_until=None, turn_token=None))
    db.commit()


async def chat_events(
    db: DB, session_id: int, text: str, messages: list[dict[str, str]],
    turn_token: str, pronunciation_hint: str | None = None,
    request_record_id: int | None = None, terminal: bool = False,
) -> AsyncIterator[dict]:
    learner_message = text
    if pronunciation_hint:
        learner_message += f"\nAssessment hint: {pronunciation_hint}"
    chunks = []
    pending = ""
    words_sent = 0
    started = perf_counter()
    stream = llm.stream_reply([*messages, {"role": "user", "content": learner_message}])
    try:
        async for token in stream:
            if not chunks:
                logger.info("Talk first token in %.3fs", perf_counter() - started)
            pending += token
            parts = pending.split()
            complete = parts if pending.endswith((" ", "\n", "\t")) else parts[:-1]
            pending = "" if pending.endswith((" ", "\n", "\t")) else (parts[-1] if parts else "")
            allowed = complete[:40 - words_sent]
            if allowed:
                text_chunk = (" " if words_sent else "") + " ".join(allowed)
                chunks.append(text_chunk)
                words_sent += len(allowed)
                yield {"type": "token", "text": text_chunk}
            if words_sent == 40:
                break
        if pending and words_sent < 40:
            text_chunk = (" " if words_sent else "") + pending
            chunks.append(text_chunk)
            yield {"type": "token", "text": text_chunk}
        reply = "".join(chunks).strip()
        if not reply:
            raise llm.LLMError("LLM returned an empty reply")
    except llm.LLMError:
        yield {"type": "error", "code": "llm_unavailable"}
        return
    finally:
        with CancelScope(shield=True):
            await stream.aclose()

    try:
        event = await run_in_threadpool(store_turn, db, session_id, text, reply, turn_token, request_record_id, terminal)
    except HTTPException:
        yield {"type": "error", "code": "turn_expired"}
        return
    except SQLAlchemyError:
        await run_in_threadpool(db.rollback)
        logger.exception("Failed to store a Talk turn")
        yield {"type": "error", "code": "database_unavailable"}
        return
    yield event


def store_turn(
    db: DB, session_id: int, text: str, reply: str, turn_token: str,
    request_record_id: int | None = None, terminal: bool = False,
) -> dict:
    # The conditional write locks the session row through the turn commit.
    result = db.execute(update(Session).where(
        Session.id == session_id, Session.turn_token == turn_token,
        Session.busy_until > datetime.now(timezone.utc).replace(tzinfo=None),
    ).values(turn_token=turn_token))
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "Turn reservation expired")
    turn = DialogueTurn(session_id=session_id, learner_text=text, tutor_text=reply)
    db.add(turn)
    db.flush()
    event = {"type": "done", "text": reply, "turn_id": turn.id}
    if request_record_id is not None:
        event = requests.record_events(db, request_record_id, [event], terminal)[0]
    db.commit()
    return event


@router.post("/chat/stream")
def chat(payload: ChatRequest, user: CurrentUser, db: DB) -> StreamingResponse:
    try:
        record_id, replay = requests.claim(db, user.id, payload.request_id, "chat", {
            "session_id": payload.session_id, "text": payload.text,
        })
        if replay is None:
            enforce_limit(db, "ai-turn", str(user.id), 20, commit=False)
            messages, token = reserve_turn(db, user.id, payload.session_id, commit=False)
            db.commit()
    except Exception:
        db.rollback()
        raise

    async def stream():
        if replay is not None:
            for event in requests.replay_events(replay):
                yield f"event: {event['type']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
            return
        try:
            async with asyncio.timeout(180):
                async with aclosing(chat_events(
                    db, payload.session_id, payload.text, messages, token,
                    request_record_id=record_id, terminal=True,
                )) as events:
                    async for event in events:
                        if event["type"] == "error":
                            await run_in_threadpool(requests.interrupt, db, record_id, event["code"])
                        event = {**event, "request_id": str(payload.request_id)}
                        yield f"event: {event['type']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
        except TimeoutError:
            await run_in_threadpool(requests.interrupt, db, record_id, "request_timeout")
            event = {"type": "error", "code": "request_timeout", "request_id": str(payload.request_id)}
            yield f"event: error\ndata: {json.dumps(event)}\n\n"
        finally:
            with CancelScope(shield=True):
                try:
                    await run_in_threadpool(requests.interrupt, db, record_id)
                finally:
                    await run_in_threadpool(release_turn, db, payload.session_id, token)

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})
