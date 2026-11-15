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
from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, StringConstraints, model_validator
from sqlalchemy import delete, select, update, or_
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from . import llm, requests
from .auth import CurrentUser, DB
from .models import AIRequest, Attempt, DialogueTurn, Session
from .prompts import coaching_prompt
from .limits import enforce_limit
from .cancellation import AIStopped, CancellationGuard, guarded_stream

router = APIRouter()
logger = logging.getLogger(__name__)
LearnerText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)]
SessionTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


class SessionCreate(BaseModel):
    topic: str = Field(default="", max_length=120)
    cefr_level: Literal["A2", "B1", "B2"] | None = None
    title: SessionTitle | None = None


class SessionView(SessionCreate):
    id: int
    cefr_level: str
    title: str
    started_at: datetime
    processing: bool


class SessionPage(BaseModel):
    items: list[SessionView]
    next_cursor: int | None


class TurnView(BaseModel):
    id: int
    text: str
    reply: str


class TurnPage(BaseModel):
    items: list[TurnView]
    next_cursor: int | None


class SessionEdit(BaseModel):
    title: SessionTitle | None = None
    topic: str | None = Field(default=None, max_length=120)
    cefr_level: Literal["A2", "B1", "B2"] | None = None

    @model_validator(mode="after")
    def reject_null(self):
        for key in self.model_fields_set:
            if getattr(self, key) is None:
                raise ValueError(f"{key} cannot be null")
        return self


def session_view(session: Session) -> SessionView:
    return SessionView(
        id=session.id, title=session.title, topic=session.topic, cefr_level=session.cefr_level,
        started_at=session.started_at.replace(tzinfo=timezone.utc),
        processing=session.busy_until is not None and session.busy_until > datetime.now(timezone.utc).replace(tzinfo=None),
    )


def owned_session(db: DB, user_id: int, session_id: int, *, lock: bool = False) -> Session:
    query = select(Session).where(Session.id == session_id, Session.user_id == user_id)
    if lock:
        # A guarded write serializes mutations on SQLite as well as PostgreSQL.
        found = db.execute(update(Session).where(
            Session.id == session_id, Session.user_id == user_id,
        ).values(title=Session.title))
        if found.rowcount != 1:
            raise HTTPException(404, "Session not found")
        query = query.with_for_update().execution_options(populate_existing=True)
    session = db.scalar(query)
    if session is None:
        raise HTTPException(404, "Session not found")
    return session


class ChatRequest(BaseModel):
    request_id: UUID
    session_id: int = Field(gt=0)
    text: LearnerText


@router.post("/sessions", status_code=201)
def create_session(payload: SessionCreate, user: CurrentUser, db: DB) -> SessionView:
    enforce_limit(db, "sessions", str(user.id), 20)
    level = payload.cefr_level or user.cefr_level
    session = Session(
        user_id=user.id, topic=payload.topic, cefr_level=level,
        title=payload.title or payload.topic.strip() or "New conversation",
    )
    db.add(session)
    db.flush()
    result = session_view(session)
    db.commit()
    return result


def dialogue_context(db: DB, user_id: int, session_id: int) -> list[dict[str, str]]:
    session = owned_session(db, user_id, session_id)
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
def list_sessions(
    user: CurrentUser, db: DB,
    before_id: int | None = Query(default=None, gt=0),
    limit: int = Query(default=50, ge=1, le=100),
    q: str | None = Query(default=None, min_length=1, max_length=120),
) -> SessionPage:
    query = select(Session).where(Session.user_id == user.id)
    if before_id is not None:
        query = query.where(Session.id < before_id)
    if q is not None:
        query = query.where(or_(Session.title.icontains(q, autoescape=True), Session.topic.icontains(q, autoescape=True)))
    rows = list(db.scalars(query.order_by(Session.id.desc()).limit(limit + 1)))
    return SessionPage(
        items=[session_view(row) for row in rows[:limit]],
        next_cursor=rows[limit - 1].id if len(rows) > limit else None,
    )


@router.get("/sessions/{session_id}")
def get_session(session_id: int, user: CurrentUser, db: DB) -> SessionView:
    return session_view(owned_session(db, user.id, session_id))


@router.patch("/sessions/{session_id}")
def edit_session(session_id: int, payload: SessionEdit, user: CurrentUser, db: DB) -> SessionView:
    session = owned_session(db, user.id, session_id, lock=True)
    if session_view(session).processing and payload.model_fields_set & {"topic", "cefr_level"}:
        raise HTTPException(409, "Session is processing another turn")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(session, key, value)
    result = session_view(session)
    db.commit()
    return result


@router.delete("/sessions/{session_id}", status_code=204)
def delete_session(session_id: int, user: CurrentUser, db: DB) -> Response:
    session = owned_session(db, user.id, session_id, lock=True)
    if session_view(session).processing:
        raise HTTPException(409, "Session is processing another turn")
    # Keep request IDs as tombstones, but remove copies of deleted conversation text.
    for record in db.scalars(select(AIRequest).where(AIRequest.session_id == session_id).with_for_update()):
        record.events_json = json.dumps([{"type": "error", "code": "session_deleted", "request_id": record.request_id}])
        record.status = "failed"
        record.session_id = None
    db.execute(update(Attempt).where(Attempt.session_id == session_id).values(session_id=None))
    db.execute(delete(DialogueTurn).where(DialogueTurn.session_id == session_id))
    db.delete(session)
    db.commit()
    return Response(status_code=204)


@router.get("/sessions/{session_id}/turns")
def list_turns(
    session_id: int, user: CurrentUser, db: DB,
    before_id: int | None = Query(default=None, gt=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> TurnPage:
    owned_session(db, user.id, session_id)
    query = select(DialogueTurn).where(DialogueTurn.session_id == session_id)
    if before_id is not None:
        query = query.where(DialogueTurn.id < before_id)
    rows = list(db.scalars(query.order_by(DialogueTurn.id.desc()).limit(limit + 1)))
    return TurnPage(
        items=[TurnView(id=row.id, text=row.learner_text, reply=row.tutor_text) for row in rows[:limit]],
        next_cursor=rows[limit - 1].id if len(rows) > limit else None,
    )


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
    guard: CancellationGuard | None = None,
) -> AsyncIterator[dict]:
    learner_message = text
    if pronunciation_hint:
        learner_message += f"\nAssessment hint: {pronunciation_hint}"
    chunks = []
    pending = ""
    words_sent = 0
    started = perf_counter()
    if guard is not None:
        await guard.check(force=True)
    stream = llm.stream_reply([*messages, {"role": "user", "content": learner_message}])
    if guard is not None:
        stream = guarded_stream(stream, guard)
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
        if guard is not None:
            await guard.check(force=True)
        yield {"type": "error", "code": "llm_unavailable"}
        return
    finally:
        with CancelScope(shield=True):
            await stream.aclose()

    try:
        event = await run_in_threadpool(store_turn, db, session_id, text, reply, turn_token, request_record_id, terminal)
    except HTTPException:
        if guard is not None:
            await guard.check(force=True)
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
    turn = DialogueTurn(session_id=session_id, learner_text=text, tutor_text=reply,
                        completed_at=datetime.now(timezone.utc).replace(tzinfo=None))
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
            requests.bind_turn(db, record_id, token)
            db.commit()
    except Exception:
        db.rollback()
        raise

    async def stream():
        if replay is not None:
            for event in requests.replay_events(replay):
                yield f"event: {event['type']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
            return
        guard = CancellationGuard(db.get_bind(), record_id)
        try:
            async with asyncio.timeout(180):
                async with aclosing(chat_events(
                    db, payload.session_id, payload.text, messages, token,
                    request_record_id=record_id, terminal=True, guard=guard,
                )) as events:
                    async for event in events:
                        if event["type"] == "error":
                            await run_in_threadpool(requests.interrupt, db, record_id, event["code"])
                        event = {**event, "request_id": str(payload.request_id)}
                        yield f"event: {event['type']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
        except AIStopped as stopped:
            await run_in_threadpool(requests.interrupt, db, record_id, stopped.code)
            event = {"type": "error", "code": stopped.code, "request_id": str(payload.request_id)}
            yield f"event: error\ndata: {json.dumps(event)}\n\n"
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
