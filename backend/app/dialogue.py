import json
import logging
from collections.abc import AsyncIterator
from time import perf_counter
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, StringConstraints
from sqlalchemy import select
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


async def chat_events(
    db: DB, session_id: int, text: str, messages: list[dict[str, str]],
    pronunciation_hint: str | None = None,
) -> AsyncIterator[dict]:
    learner_message = text
    if pronunciation_hint:
        learner_message += f"\nAssessment hint: {pronunciation_hint}"
    chunks = []
    started = perf_counter()
    try:
        async for token in llm.stream_reply([*messages, {"role": "user", "content": learner_message}]):
            if not chunks:
                logger.info("Talk first token in %.3fs", perf_counter() - started)
            chunks.append(token)
            yield {"type": "token", "text": token}
        reply = "".join(chunks).strip()
        if not reply:
            raise llm.LLMError("LLM returned an empty reply")
    except llm.LLMError:
        yield {"type": "error", "code": "llm_unavailable"}
        return

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
    messages = dialogue_context(db, user.id, payload.session_id)
    db.rollback()  # Release the read transaction before waiting for the LLM.

    async def stream():
        async for event in chat_events(db, payload.session_id, payload.text, messages):
            yield f"event: {event['type']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})
