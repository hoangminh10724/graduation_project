import json
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter
from pydantic import BaseModel, ValidationError
from sqlalchemy import select

from .auth import CurrentUser, DB
from .models import Attempt
from .speech import Assessment

router = APIRouter()


class ProgressView(BaseModel):
    attempts: int
    streak_days: int
    phoneme_averages: dict[str, float]


def streak(days: set[date], today: date) -> int:
    day = today if today in days else today - timedelta(days=1)
    count = 0
    while day in days:
        count += 1
        day -= timedelta(days=1)
    return count


@router.get("/progress")
def get_progress(user: CurrentUser, db: DB) -> ProgressView:
    attempts = db.execute(
        select(Attempt.created_at, Attempt.detail_json)
        .where(Attempt.user_id == user.id).execution_options(yield_per=100)
    )
    sums: dict[str, float] = defaultdict(float)
    counts: dict[str, int] = defaultdict(int)
    days = set()
    total = 0
    for created_at, detail_json in attempts:
        total += 1
        days.add(created_at.date())
        try:
            assessment = Assessment.model_validate_json(detail_json)
        except ValidationError:
            continue
        for word in assessment.words:
            for phoneme in word.phonemes:
                sums[phoneme.ipa] += phoneme.score
                counts[phoneme.ipa] += 1
    return ProgressView(
        attempts=total,
        streak_days=streak(days, datetime.now(timezone.utc).date()),
        phoneme_averages={ipa: round(score / counts[ipa], 2) for ipa, score in sums.items()},
    )


def store_attempt(db: DB, user_id: int, text: str, assessment: dict) -> None:
    db.add(Attempt(
        user_id=user_id, text=text, sentence_score=assessment["sentence_score"],
        detail_json=json.dumps(assessment, ensure_ascii=False),
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    ))
    db.commit()
