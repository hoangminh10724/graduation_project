import json
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from .auth import CurrentUser, DB
from .cards import CardView, card_view, check_deck
from .limits import enforce_limit
from .models import Card, StudyItem, StudySession
from .study_state import now, owned_study, refresh_queue

router = APIRouter(prefix="/study-sessions")


class StudyCreate(BaseModel):
    request_id: UUID
    deck_id: int | None = Field(default=None, gt=0)
    limit: int = Field(default=20, ge=1, le=100, strict=True)


class StudySummary(BaseModel):
    id: int
    deck_id: int | None
    status: Literal["active", "completed"]
    started_at: datetime
    finished_at: datetime | None
    elapsed_seconds: int
    selected: int
    reviewed: int
    skipped: int
    remaining: int
    ratings: dict[str, int]
    skipped_reasons: dict[str, int]


class StudyDetail(StudySummary):
    queue: list[CardView]


class StudyPage(BaseModel):
    items: list[StudySummary]
    next_cursor: int | None


def summaries(db: DB, studies: list[StudySession]) -> list[StudySummary]:
    totals = {study.id: {
        "selected": 0, "reviewed": 0, "skipped": 0, "remaining": 0,
        "ratings": {"again": 0, "hard": 0, "good": 0, "easy": 0}, "skipped_reasons": {},
    } for study in studies}
    if totals:
        rows = db.execute(select(
            StudyItem.study_session_id, StudyItem.state, StudyItem.rating, StudyItem.skip_reason, func.count(),
        ).where(StudyItem.study_session_id.in_(totals)).group_by(
            StudyItem.study_session_id, StudyItem.state, StudyItem.rating, StudyItem.skip_reason,
        ))
        for study_id, state, rating, reason, count in rows:
            total = totals[study_id]
            total["selected"] += count
            total[{"pending": "remaining", "reviewed": "reviewed", "skipped": "skipped"}[state]] += count
            if rating is not None:
                total["ratings"][{1: "again", 2: "hard", 3: "good", 4: "easy"}[rating]] += count
            if reason is not None:
                total["skipped_reasons"][reason] = total["skipped_reasons"].get(reason, 0) + count
    return [StudySummary(
        id=study.id, deck_id=study.deck_id, status=study.status,
        started_at=study.started_at.replace(tzinfo=timezone.utc),
        finished_at=study.finished_at.replace(tzinfo=timezone.utc) if study.finished_at else None,
        elapsed_seconds=max(0, int(((study.finished_at or now()) - study.started_at).total_seconds())),
        **totals[study.id],
    ) for study in studies]


def detail(db: DB, study: StudySession) -> StudyDetail:
    refresh_queue(db, study)
    db.flush()
    queue = list(db.scalars(select(Card).join(StudyItem, StudyItem.card_id == Card.id).where(
        StudyItem.study_session_id == study.id, StudyItem.state == "pending",
    ).order_by(StudyItem.position)))
    return StudyDetail(**summaries(db, [study])[0].model_dump(), queue=[card_view(card) for card in queue])


def replay_creation(db: DB, user_id: int, study: StudySession, selection: str) -> StudyDetail:
    if study.selection_json != selection:
        raise HTTPException(409, "Request ID already used for a different study selection")
    result = detail(db, owned_study(db, user_id, study.id))
    db.commit()
    return result


@router.post("", status_code=201)
def create_study(payload: StudyCreate, user: CurrentUser, db: DB) -> StudyDetail:
    user_id = user.id
    selection = json.dumps({"deck_id": payload.deck_id, "limit": payload.limit}, sort_keys=True)
    previous = db.scalar(select(StudySession).where(
        StudySession.user_id == user_id, StudySession.request_id == str(payload.request_id),
    ))
    if previous is not None:
        return replay_creation(db, user_id, previous, selection)
    enforce_limit(db, "study-create", str(user_id), 20)
    check_deck(db, user_id, payload.deck_id)
    active = db.scalar(select(StudySession.id).where(StudySession.user_id == user_id, StudySession.status == "active"))
    if active is not None:
        current = owned_study(db, user_id, active)
        if current.request_id == str(payload.request_id):
            return replay_creation(db, user_id, current, selection)
        refresh_queue(db, current)
        if current.status == "active":
            raise HTTPException(409, {"code": "study_session_active", "study_session_id": active})
        db.flush()
    query = select(Card).where(Card.user_id == user_id, Card.suspended.is_(False), Card.due <= now())
    if payload.deck_id is not None:
        query = query.where(Card.deck_id == payload.deck_id)
    cards = list(db.scalars(query.order_by(Card.due, Card.id).limit(payload.limit)))
    study = StudySession(
        user_id=user_id, request_id=str(payload.request_id), selection_json=selection,
        deck_id=payload.deck_id, status="active" if cards else "completed",
        started_at=now(), finished_at=None if cards else now(),
    )
    try:
        db.add(study)
        db.flush()
        for position, card in enumerate(cards):
            db.add(StudyItem(study_session_id=study.id, card_id=card.id, position=position,
                             expected_due=card.due, state="pending"))
        db.flush()
        result = detail(db, study)
        db.commit()
    except IntegrityError:
        db.rollback()
        previous = db.scalar(select(StudySession).where(
            StudySession.user_id == user_id, StudySession.request_id == str(payload.request_id),
        ))
        if previous is not None:
            return replay_creation(db, user_id, previous, selection)
        active = db.scalar(select(StudySession.id).where(StudySession.user_id == user_id, StudySession.status == "active"))
        raise HTTPException(409, {"code": "study_selection_conflict", "study_session_id": active}) from None
    return result


@router.get("")
def list_studies(
    user: CurrentUser, db: DB, before_id: int | None = Query(default=None, gt=0),
    limit: int = Query(default=20, ge=1, le=100), status: Literal["active", "completed"] | None = None,
) -> StudyPage:
    query = select(StudySession).where(StudySession.user_id == user.id)
    if before_id is not None:
        query = query.where(StudySession.id < before_id)
    if status is not None:
        query = query.where(StudySession.status == status)
    rows = list(db.scalars(query.order_by(StudySession.id.desc()).limit(limit + 1)))
    return StudyPage(items=summaries(db, rows[:limit]), next_cursor=rows[limit - 1].id if len(rows) > limit else None)


@router.get("/{study_id}")
def get_study(study_id: int, user: CurrentUser, db: DB) -> StudyDetail:
    result = detail(db, owned_study(db, user.id, study_id))
    db.commit()
    return result


@router.post("/{study_id}/finish")
def finish_study(study_id: int, user: CurrentUser, db: DB) -> StudyDetail:
    study = owned_study(db, user.id, study_id)
    refresh_queue(db, study)
    if study.status == "active":
        db.execute(update(StudyItem).where(StudyItem.study_session_id == study.id, StudyItem.state == "pending").values(
            state="skipped", skip_reason="ended_early",
        ))
        study.status, study.finished_at = "completed", now()
    result = detail(db, study)
    db.commit()
    return result
