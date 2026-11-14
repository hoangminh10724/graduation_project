from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ValidationError
from sqlalchemy import select

from .auth import CurrentUser, DB
from .models import Attempt, Session
from .speech import Assessment

router = APIRouter(prefix="/attempts")


class AttemptSummary(BaseModel):
    id: int
    assessment_text: str
    reference_text: str | None
    transcript: str | None
    session_id: int | None
    sentence_score: float
    created_at: datetime


class AttemptDetail(AttemptSummary):
    assessment: Assessment | None


class AttemptPage(BaseModel):
    items: list[AttemptSummary]
    next_cursor: int | None


def summary(attempt: Attempt) -> AttemptSummary:
    return AttemptSummary(
        id=attempt.id, assessment_text=attempt.text,
        reference_text=attempt.reference_text, transcript=attempt.transcript,
        session_id=attempt.session_id, sentence_score=attempt.sentence_score,
        created_at=attempt.created_at.replace(tzinfo=timezone.utc),
    )


@router.get("")
def list_attempts(
    user: CurrentUser, db: DB,
    before_id: int | None = Query(default=None, gt=0),
    limit: int = Query(default=50, ge=1, le=100),
    q: str | None = Query(default=None, min_length=1, max_length=200),
    session_id: int | None = Query(default=None, gt=0),
) -> AttemptPage:
    query = select(Attempt).where(Attempt.user_id == user.id)
    if session_id is not None:
        owned = db.scalar(select(Session.id).where(Session.id == session_id, Session.user_id == user.id))
        if owned is None:
            raise HTTPException(404, "Session not found")
        query = query.where(Attempt.session_id == session_id)
    if before_id is not None:
        query = query.where(Attempt.id < before_id)
    if q is not None:
        query = query.where(Attempt.text.icontains(q, autoescape=True))
    rows = list(db.scalars(query.order_by(Attempt.id.desc()).limit(limit + 1)))
    items = [summary(row) for row in rows[:limit]]
    return AttemptPage(items=items, next_cursor=items[-1].id if len(rows) > limit else None)


@router.get("/{attempt_id}")
def get_attempt(attempt_id: int, user: CurrentUser, db: DB) -> AttemptDetail:
    attempt = db.scalar(select(Attempt).where(Attempt.id == attempt_id, Attempt.user_id == user.id))
    if attempt is None:
        raise HTTPException(404, "Attempt not found")
    try:
        assessment = Assessment.model_validate_json(attempt.detail_json)
    except ValidationError:
        assessment = None
    return AttemptDetail(**summary(attempt).model_dump(), assessment=assessment)
