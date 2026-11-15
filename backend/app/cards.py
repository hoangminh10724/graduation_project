from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.exc import IntegrityError

from . import fsrs
from .auth import CurrentUser, DB
from .models import Card, Deck, Review, StudyItem
from .study_state import finish_if_empty, owned_study, study_item_for_review

router = APIRouter()
CardText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)]


class CardCreate(BaseModel):
    front: CardText
    back: CardText
    deck_id: int | None = Field(default=None, gt=0)


class CardView(CardCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    due: datetime
    stability: float
    difficulty: float
    suspended: bool = False


class CardEdit(BaseModel):
    front: CardText | None = None
    back: CardText | None = None
    deck_id: int | None = Field(default=None, gt=0)
    suspended: bool | None = None

    @model_validator(mode="after")
    def disallow_null_content(self):
        for field in ("front", "back", "suspended"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class CardPage(BaseModel):
    items: list[CardView]
    next_cursor: int | None


class ReviewCreate(BaseModel):
    request_id: UUID
    card_id: int = Field(gt=0)
    rating: int = Field(strict=True, ge=1, le=4)
    study_session_id: int | None = Field(default=None, gt=0)


class ReviewResult(BaseModel):
    card: CardView
    interval_days: int
    interval_seconds: int
    study_session_id: int | None = None


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def card_view(card: Card) -> CardView:
    return CardView.model_validate(card).model_copy(
        update={"due": card.due.replace(tzinfo=timezone.utc)}
    )


def owned_card(db: DB, user_id: int, card_id: int, *, lock: bool = False) -> Card:
    query = select(Card).where(Card.id == card_id, Card.user_id == user_id)
    if lock:
        query = query.with_for_update()
    card = db.scalar(query)
    if card is None:
        raise HTTPException(404, "Card not found")
    return card


def check_deck(db: DB, user_id: int, deck_id: int | None) -> None:
    if deck_id is not None and db.scalar(select(Deck.id).where(
        Deck.id == deck_id, Deck.user_id == user_id
    ).with_for_update()) is None:
        raise HTTPException(404, "Deck not found")


@router.post("/cards", status_code=201)
def create_card(payload: CardCreate, user: CurrentUser, db: DB) -> CardView:
    check_deck(db, user.id, payload.deck_id)
    card = Card(**payload.model_dump(), user_id=user.id, due=utc_now())
    db.add(card)
    db.flush()
    result = card_view(card)
    db.commit()
    return result


@router.get("/cards/due")
def due_cards(
    user: CurrentUser, db: DB, limit: int = Query(default=50, ge=1, le=100),
    deck_id: int | None = Query(default=None, gt=0),
) -> list[CardView]:
    query = select(Card).where(
        Card.user_id == user.id, Card.due <= utc_now(), Card.suspended.is_(False)
    )
    if deck_id is not None:
        query = query.where(Card.deck_id == deck_id)
    cards = db.scalars(
        query.order_by(Card.due, Card.id).limit(limit)
    )
    return [card_view(card) for card in cards]


@router.get("/cards")
def list_cards(
    user: CurrentUser, db: DB, cursor: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    q: str = Query(default="", max_length=200),
    deck_id: int | None = Query(default=None, gt=0),
    suspended: bool | None = None,
) -> CardPage:
    query = select(Card).where(Card.user_id == user.id, Card.id > cursor)
    if q:
        query = query.where(or_(
            Card.front.icontains(q, autoescape=True), Card.back.icontains(q, autoescape=True)
        ))
    if deck_id is not None:
        query = query.where(Card.deck_id == deck_id)
    if suspended is not None:
        query = query.where(Card.suspended == suspended)
    rows = list(db.scalars(query.order_by(Card.id).limit(limit + 1)))
    return CardPage(
        items=[card_view(row) for row in rows[:limit]],
        next_cursor=rows[limit - 1].id if len(rows) > limit else None,
    )


@router.get("/cards/{card_id}")
def get_card(card_id: int, user: CurrentUser, db: DB) -> CardView:
    return card_view(owned_card(db, user.id, card_id))


@router.patch("/cards/{card_id}")
def edit_card(card_id: int, payload: CardEdit, user: CurrentUser, db: DB) -> CardView:
    check_deck(db, user.id, payload.deck_id)
    card = owned_card(db, user.id, card_id, lock=True)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(card, key, value)
    result = card_view(card)
    db.commit()
    return result


@router.delete("/cards/{card_id}", status_code=204)
def delete_card(card_id: int, user: CurrentUser, db: DB) -> Response:
    card = owned_card(db, user.id, card_id, lock=True)
    db.execute(delete(Review).where(Review.card_id == card.id))
    db.execute(update(StudyItem).where(StudyItem.card_id == card.id).values(card_id=None))
    db.delete(card)
    db.commit()
    return Response(status_code=204)


@router.get("/cards/{card_id}/reviews")
def review_history(
    card_id: int, user: CurrentUser, db: DB,
    before_id: int | None = Query(default=None, gt=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> dict:
    owned_card(db, user.id, card_id)
    query = select(Review).where(Review.card_id == card_id)
    if before_id is not None:
        query = query.where(Review.id < before_id)
    rows = list(db.scalars(query.order_by(Review.id.desc()).limit(limit + 1)))
    return {
        "items": [{
            "id": row.id, "rating": row.rating,
            "reviewed_at": row.reviewed_at.replace(tzinfo=timezone.utc),
        } for row in rows[:limit]],
        "next_cursor": rows[limit - 1].id if len(rows) > limit else None,
    }


def scheduled_review(card: Card, last: datetime | None, rating: int, now: datetime) -> tuple[fsrs.Card, timedelta]:
    state = fsrs.Card(
        due=card.due.replace(tzinfo=timezone.utc),
        stability=card.stability,
        difficulty=card.difficulty,
        last_review=last.replace(tzinfo=timezone.utc) if last else None,
    )
    updated, interval = fsrs.review(state, rating, now.replace(tzinfo=timezone.utc))
    # Product learning policy layered on top of the FSRS memory model.
    if rating == 1:
        interval = timedelta(minutes=10)
    return updated, interval


@router.get("/cards/{card_id}/schedule")
def preview_schedule(card_id: int, user: CurrentUser, db: DB) -> dict:
    card = owned_card(db, user.id, card_id)
    if card.suspended:
        raise HTTPException(409, "Card is suspended")
    last = db.scalar(select(func.max(Review.reviewed_at)).where(Review.card_id == card.id))
    now = utc_now()
    choices = []
    for rating in fsrs.Rating:
        updated, interval = scheduled_review(card, last, rating, now)
        choices.append({
            "rating": int(rating), "label": rating.name.title(),
            "interval_seconds": int(interval.total_seconds()),
            "due": (now + interval).replace(tzinfo=timezone.utc),
            "stability": updated.stability, "difficulty": updated.difficulty,
        })
    return {"card_id": card.id, "calculated_at": now.replace(tzinfo=timezone.utc), "choices": choices}


@router.post("/reviews")
def review_card(payload: ReviewCreate, user: CurrentUser, db: DB) -> ReviewResult:
    study = owned_study(db, user.id, payload.study_session_id) if payload.study_session_id is not None else None
    card = db.scalar(
        select(Card).where(Card.id == payload.card_id, Card.user_id == user.id).with_for_update()
    )
    if card is None:
        raise HTTPException(404, "Card not found")
    previous = db.scalar(select(Review).where(Review.request_id == str(payload.request_id)))
    if previous:
        if previous.card_id != card.id or previous.rating != payload.rating or previous.study_session_id != payload.study_session_id:
            raise HTTPException(409, "Request ID already used for a different review")
        return ReviewResult.model_validate_json(previous.result_json)
    if card.suspended:
        raise HTTPException(409, "Card is suspended")
    item = study_item_for_review(db, study, card) if study is not None else None
    last = db.scalar(select(func.max(Review.reviewed_at)).where(Review.card_id == card.id))
    now = utc_now()
    updated, interval = scheduled_review(card, last, payload.rating, now)
    card.stability, card.difficulty = updated.stability, updated.difficulty
    card.due = now + interval
    result = ReviewResult(
        card=card_view(card), interval_days=interval.days, interval_seconds=int(interval.total_seconds()),
        study_session_id=payload.study_session_id,
    )
    db.add(Review(
        card_id=card.id, rating=payload.rating, reviewed_at=now,
        request_id=str(payload.request_id), result_json=result.model_dump_json(),
        study_session_id=payload.study_session_id,
    ))
    try:
        if item is not None:
            item.state, item.rating, item.reviewed_at = "reviewed", payload.rating, now
            db.flush()
            finish_if_empty(db, study)
        db.commit()
    except IntegrityError:
        db.rollback()
        previous = db.scalar(select(Review).where(Review.request_id == str(payload.request_id)))
        if previous and previous.card_id == payload.card_id and previous.rating == payload.rating and previous.study_session_id == payload.study_session_id:
            return ReviewResult.model_validate_json(previous.result_json)
        raise HTTPException(409, "Conflicting review request") from None
    return result
