import json
import logging
from collections.abc import AsyncIterator
from time import perf_counter
from typing import Annotated, Literal
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, StringConstraints
from sqlalchemy import select, update, or_
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from . import llm
from .auth import CurrentUser, DB
from .models import DialogueTurn, Session
from .prompts import coaching_prompt

router = APIRouter()
logger = logging.getLogger(__name__)
LearnerText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)]


class SessionCreate(BaseModel):
    topic: str = Field(default="", max_length=120)
    cefr_level: Literal["A2", "B1", "B2"] = "A2"


class SessionView(SessionCreate):
    id: int


class ChatRequest(BaseModel):
    session_id: int = Field(gt=0)
    text: LearnerText


@router.post("/sessions", status_code=201)
def create_session(payload: SessionCreate, user: CurrentUser, db: DB) -> SessionView:
    session = Session(user_id=user.id, **payload.model_dump())
    db.add(session)
    db.flush()
    result = SessionView(id=session.id, **payload.model_dump())
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


def reserve_turn(db: DB, user_id: int, session_id: int) -> tuple[list[dict[str, str]], str]:
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
    db.commit()
    try:
        messages = dialogue_context(db, user_id, session_id)
        db.rollback()
        return messages, token
    except Exception:
        release_turn(db, session_id, token)
        raise


def release_turn(db: DB, session_id: int, token: str) -> None:
    db.rollback()
    db.execute(update(Session).where(
        Session.id == session_id, Session.turn_token == token
    ).values(busy_until=None, turn_token=None))
    db.commit()


async def chat_events(
    db: DB, session_id: int, text: str, messages: list[dict[str, str]],
    pronunciation_hint: str | None = None,
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
        await stream.aclose()

    try:
        await run_in_threadpool(store_turn, db, session_id, text, reply)
    except SQLAlchemyError:
        await run_in_threadpool(db.rollback)
        logger.exception("Failed to store a Talk turn")
        yield {"type": "error", "code": "database_unavailable"}
        return
    yield {"type": "done", "text": reply}


def store_turn(db: DB, session_id: int, text: str, reply: str) -> None:
    db.add(DialogueTurn(session_id=session_id, learner_text=text, tutor_text=reply))
    db.commit()


@router.post("/chat/stream")
def chat(payload: ChatRequest, user: CurrentUser, db: DB) -> StreamingResponse:
    messages, token = reserve_turn(db, user.id, payload.session_id)

    async def stream():
        try:
            async for event in chat_events(db, payload.session_id, payload.text, messages):
                yield f"event: {event['type']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
        finally:
            release_turn(db, payload.session_id, token)

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})
