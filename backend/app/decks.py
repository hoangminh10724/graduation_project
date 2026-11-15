from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, StringConstraints
from sqlalchemy import select, update

from .auth import CurrentUser, DB
from .models import Card, Deck, StudySession

router = APIRouter(prefix="/decks")


class DeckInput(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
    description: Annotated[str, StringConstraints(max_length=1000)] = ""


class DeckView(DeckInput):
    model_config = ConfigDict(from_attributes=True)
    id: int


def owned_deck(db: DB, user_id: int, deck_id: int) -> Deck:
    deck = db.scalar(select(Deck).where(
        Deck.id == deck_id, Deck.user_id == user_id
    ).with_for_update())
    if deck is None:
        raise HTTPException(404, "Deck not found")
    return deck


@router.post("", status_code=201)
def create_deck(payload: DeckInput, user: CurrentUser, db: DB) -> DeckView:
    deck = Deck(user_id=user.id, **payload.model_dump())
    db.add(deck)
    db.flush()
    result = DeckView.model_validate(deck)
    db.commit()
    return result


@router.get("")
def list_decks(
    user: CurrentUser, db: DB,
    cursor: int = Query(default=0, ge=0), limit: int = Query(default=50, ge=1, le=100),
) -> dict:
    decks = list(db.scalars(select(Deck).where(
        Deck.user_id == user.id, Deck.id > cursor
    ).order_by(Deck.id).limit(limit + 1)))
    return {
        "items": [DeckView.model_validate(deck) for deck in decks[:limit]],
        "next_cursor": decks[limit - 1].id if len(decks) > limit else None,
    }


@router.put("/{deck_id}")
def edit_deck(deck_id: int, payload: DeckInput, user: CurrentUser, db: DB) -> DeckView:
    deck = owned_deck(db, user.id, deck_id)
    deck.name = payload.name
    deck.description = payload.description
    result = DeckView.model_validate(deck)
    db.commit()
    return result


@router.delete("/{deck_id}", status_code=204)
def delete_deck(deck_id: int, user: CurrentUser, db: DB) -> Response:
    deck = owned_deck(db, user.id, deck_id)
    # Deleting a collection keeps its cards and their review history.
    db.execute(update(StudySession).where(StudySession.deck_id == deck.id).values(deck_id=None))
    db.execute(update(Card).where(Card.deck_id == deck.id).values(deck_id=None))
    db.delete(deck)
    db.commit()
    return Response(status_code=204)
