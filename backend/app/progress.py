import json
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ValidationError
from sqlalchemy import select

from .auth import CurrentUser, DB
from .models import Attempt
from .speech import Assessment
from . import requests

router = APIRouter()


class ProgressView(BaseModel):
    attempts: int
    streak_days: int
    phoneme_averages: dict[str, float]
    timezone: str
    daily: list[dict]
    date_from: date | None = None
    date_to: date | None = None
    weak_phonemes: list[dict]


def streak(days: set[date], today: date) -> int:
    day = today if today in days else today - timedelta(days=1)
    count = 0
    while day in days:
        count += 1
        day -= timedelta(days=1)
    return count


@router.get("/progress")
def get_progress(
    user: CurrentUser, db: DB, timezone_name: str | None = None,
    date_from: date | None = None, date_to: date | None = None,
) -> ProgressView:
    timezone_name = timezone_name or user.timezone_name
    try:
        zone = ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError):
        raise HTTPException(422, "Unknown timezone") from None
    if (date_from is None) != (date_to is None):
        raise HTTPException(422, "Provide both date_from and date_to")
    query = select(Attempt.created_at, Attempt.detail_json, Attempt.sentence_score).where(Attempt.user_id == user.id)
    if date_from is not None:
        if date_to < date_from or (date_to - date_from).days > 365 or date_to == date.max:
            raise HTTPException(422, "Date range must contain 1 to 366 days")
        try:
            start = datetime.combine(date_from, datetime.min.time(), tzinfo=zone).astimezone(timezone.utc).replace(tzinfo=None)
            end = datetime.combine(date_to + timedelta(days=1), datetime.min.time(), tzinfo=zone).astimezone(timezone.utc).replace(tzinfo=None)
        except (OverflowError, ValueError):
            raise HTTPException(422, "Date range outside supported timestamps") from None
        query = query.where(Attempt.created_at >= start, Attempt.created_at < end)
    attempts = db.execute(query.execution_options(yield_per=100))
    sums: dict[str, float] = defaultdict(float)
    counts: dict[str, int] = defaultdict(int)
    days = set()
    daily = {}
    total = 0
    for created_at, detail_json, sentence_score in attempts:
        total += 1
        day = created_at.replace(tzinfo=timezone.utc).astimezone(zone).date()
        days.add(day)
        stats = daily.setdefault(day, {"attempts": 0, "score": 0.0, "sums": defaultdict(float), "counts": defaultdict(int)})
        stats["attempts"] += 1
        stats["score"] += sentence_score
        try:
            assessment = Assessment.model_validate_json(detail_json)
        except ValidationError:
            continue
        for word in assessment.words:
            for phoneme in word.phonemes:
                sums[phoneme.ipa] += phoneme.score
                counts[phoneme.ipa] += 1
                stats["sums"][phoneme.ipa] += phoneme.score
                stats["counts"][phoneme.ipa] += 1
    if date_from is not None:
        # Filtering the chart must not reset the learner's current streak.
        days = {
            timestamp.replace(tzinfo=timezone.utc).astimezone(zone).date()
            for timestamp in db.scalars(select(Attempt.created_at).where(Attempt.user_id == user.id).execution_options(yield_per=100))
        }
        day = date_from
        while day <= date_to:
            daily.setdefault(day, {"attempts": 0, "score": 0.0, "sums": {}, "counts": {}})
            day += timedelta(days=1)
    averages = {ipa: round(score / counts[ipa], 2) for ipa, score in sums.items()}
    return ProgressView(
        attempts=total,
        streak_days=streak(days, datetime.now(zone).date()),
        phoneme_averages=averages,
        date_from=date_from, date_to=date_to,
        weak_phonemes=[{"ipa": ipa, "average": averages[ipa], "samples": counts[ipa]}
                       for ipa in sorted(averages, key=lambda ipa: (averages[ipa], ipa))[:5]],
        timezone=timezone_name,
        daily=[{
            "date": day.isoformat(), "attempts": stats["attempts"],
            "sentence_average": round(stats["score"] / stats["attempts"], 2) if stats["attempts"] else None,
            "phoneme_averages": {ipa: round(score / stats["counts"][ipa], 2) for ipa, score in stats["sums"].items()},
        } for day, stats in sorted(daily.items())],
    )


def store_attempt(
    db: DB, user_id: int, text: str, assessment: dict,
    reference_text: str | None = None, transcript: str | None = None,
    session_id: int | None = None,
    request_record_id: int | None = None,
) -> int:
    assessment = Assessment.model_validate(assessment).model_dump()
    attempt = Attempt(
        user_id=user_id, text=text, sentence_score=assessment["sentence_score"],
        reference_text=reference_text, transcript=transcript, session_id=session_id,
        detail_json=json.dumps(assessment, ensure_ascii=False),
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(attempt)
    db.flush()
    attempt_id = attempt.id
    if request_record_id is not None:
        events = [{"type": "final", "text": text, "assessment": assessment, "attempt_id": attempt_id}]
        if assessment["hints"] or assessment["errors"]:
            events.append({"type": "coaching", "hints": assessment["hints"], "errors": assessment["errors"]})
        requests.record_events(db, request_record_id, events, terminal=True)
    db.commit()
    return attempt_id
