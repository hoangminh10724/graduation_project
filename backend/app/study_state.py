from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, select, update

from .auth import DB
from .models import Card, StudyItem, StudySession


def now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def owned_study(db: DB, user_id: int, study_id: int) -> StudySession:
    found = db.execute(update(StudySession).where(
        StudySession.id == study_id, StudySession.user_id == user_id,
    ).values(status=StudySession.status))
    if found.rowcount != 1:
        raise HTTPException(404, "Study session not found")
    return db.scalar(select(StudySession).where(StudySession.id == study_id).execution_options(populate_existing=True))


def finish_if_empty(db: DB, study: StudySession) -> None:
    pending = db.scalar(select(func.count()).select_from(StudyItem).where(
        StudyItem.study_session_id == study.id, StudyItem.state == "pending",
    ))
    if study.status == "active" and not pending:
        study.status = "completed"
        study.finished_at = now()


def refresh_queue(db: DB, study: StudySession) -> None:
    if study.status != "active":
        return
    for item, card in db.execute(select(StudyItem, Card).outerjoin(Card, Card.id == StudyItem.card_id).where(
        StudyItem.study_session_id == study.id, StudyItem.state == "pending",
    )):
        reason = None
        if card is None:
            reason = "card_deleted"
        elif card.suspended:
            reason = "card_suspended"
        elif card.due != item.expected_due:
            reason = "schedule_changed"
        if reason:
            item.state, item.skip_reason = "skipped", reason
    db.flush()
    finish_if_empty(db, study)


def study_item_for_review(db: DB, study: StudySession, card: Card) -> StudyItem:
    item = db.scalar(select(StudyItem).where(
        StudyItem.study_session_id == study.id, StudyItem.card_id == card.id,
    ))
    if study.status != "active":
        raise HTTPException(409, "Study session is completed")
    if item is None or item.state != "pending":
        raise HTTPException(409, "Card is not pending in this study session")
    if card.due != item.expected_due or card.due > now():
        raise HTTPException(409, "Card schedule changed; reload the study session")
    return item
