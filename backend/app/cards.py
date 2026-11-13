from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from . import fsrs
from .auth import CurrentUser, DB
from .models import Card, Review

router = APIRouter()
CardText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)]


class CardCreate(BaseModel):
    front: CardText
    back: CardText


class CardView(CardCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    due: datetime
    stability: float
    difficulty: float


class ReviewCreate(BaseModel):
    request_id: UUID
    card_id: int = Field(gt=0)
    rating: int = Field(strict=True, ge=1, le=4)


class ReviewResult(BaseModel):
    card: CardView
    interval_days: int
    interval_seconds: int


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def card_view(card: Card) -> CardView:
    return CardView.model_validate(card).model_copy(
        update={"due": card.due.replace(tzinfo=timezone.utc)}
    )


@router.post("/cards", status_code=201)
def create_card(payload: CardCreate, user: CurrentUser, db: DB) -> CardView:
    card = Card(**payload.model_dump(), user_id=user.id, due=utc_now())
    db.add(card)
    db.flush()
    result = card_view(card)
    db.commit()
    return result


@router.get("/cards/due")
def due_cards(user: CurrentUser, db: DB) -> list[CardView]:
    cards = db.scalars(
        select(Card).where(Card.user_id == user.id, Card.due <= utc_now())
        .order_by(Card.due, Card.id)
    )
    return [card_view(card) for card in cards]


@router.post("/reviews")
def review_card(payload: ReviewCreate, user: CurrentUser, db: DB) -> ReviewResult:
    card = db.scalar(
        select(Card).where(Card.id == payload.card_id, Card.user_id == user.id).with_for_update()
    )
    if card is None:
        raise HTTPException(404, "Card not found")
    previous = db.scalar(select(Review).where(Review.request_id == str(payload.request_id)))
    if previous:
        if previous.card_id != card.id or previous.rating != payload.rating:
            raise HTTPException(409, "Request ID already used for a different review")
        return ReviewResult.model_validate_json(previous.result_json)
    last = db.scalar(select(func.max(Review.reviewed_at)).where(Review.card_id == card.id))
    now = utc_now()
    state = fsrs.Card(
        due=card.due.replace(tzinfo=timezone.utc),
        stability=card.stability,
        difficulty=card.difficulty,
        last_review=last.replace(tzinfo=timezone.utc) if last else None,
    )
    updated, interval = fsrs.review(state, payload.rating, now.replace(tzinfo=timezone.utc))
    # Product learning policy layered on top of the FSRS memory model.
    if payload.rating == 1:
        interval = timedelta(minutes=10)
    card.stability, card.difficulty = updated.stability, updated.difficulty
    card.due = now + interval
    result = ReviewResult(
        card=card_view(card), interval_days=interval.days, interval_seconds=int(interval.total_seconds())
    )
    db.add(Review(
        card_id=card.id, rating=payload.rating, reviewed_at=now,
        request_id=str(payload.request_id), result_json=result.model_dump_json(),
    ))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        previous = db.scalar(select(Review).where(Review.request_id == str(payload.request_id)))
        if previous and previous.card_id == payload.card_id and previous.rating == payload.rating:
            return ReviewResult.model_validate_json(previous.result_json)
        raise HTTPException(409, "Conflicting review request") from None
    return result
