from datetime import date, datetime, timezone
import pytest
from fastapi import HTTPException

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models import Attempt, Base, User
from app.progress import get_progress
from app.speech import Assessment
from test_cards import api, register


def test_daily_progress_uses_local_date_and_preserves_coaching():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    assessment = Assessment.model_validate({
        "sentence_score": 70, "words": [],
        "hints": ["Put your tongue between your teeth."],
        "errors": [{"ipa": "θ", "type": "substitution", "actual": "s"}],
    })
    assert assessment.model_dump()["errors"][0]["actual"] == "s"
    with Session(engine) as db:
        user = User(email="local@example.com", password_hash="unused")
        db.add(user)
        db.flush()
        db.add(Attempt(
            user_id=user.id, text="think", sentence_score=70,
            detail_json=assessment.model_dump_json(), created_at=datetime(2026, 1, 1, 18),
        ))
        db.commit()
        local = get_progress(user, db)
        utc = get_progress(user, db, "UTC")
        assert local.daily[0]["date"] == "2026-01-02"
        assert utc.daily[0]["date"] == "2026-01-01"
        assert local.daily[0]["sentence_average"] == 70
    engine.dispose()


@pytest.mark.parametrize("day,start,end", [
    (date(2026, 3, 8), datetime(2026, 3, 8, 5), datetime(2026, 3, 9, 4)),
    (date(2026, 11, 1), datetime(2026, 11, 1, 4), datetime(2026, 11, 2, 5)),
])
def test_progress_http_dst_window(api, day, start, end):
    from datetime import timedelta
    from sqlalchemy import select

    client, engine = api
    owner = register(client, "dst@example.test")
    other = register(client, "private@example.test")
    with Session(engine) as db:
        user = db.scalar(select(User).where(User.email == "dst@example.test"))
        for timestamp in (start - timedelta(microseconds=1), start,
                          end - timedelta(microseconds=1), end):
            db.add(Attempt(user_id=user.id, text="test", sentence_score=60,
                           detail_json='{"sentence_score":60,"words":[]}', created_at=timestamp))
        db.commit()
    params = {"timezone_name": "America/New_York", "date_from": day.isoformat(), "date_to": day.isoformat()}
    response = client.get("/progress", params=params, headers=owner)
    assert response.status_code == 200
    assert response.json()["attempts"] == 2
    assert response.json()["daily"][0]["date"] == day.isoformat()
    assert client.get("/progress", params=params, headers=other).json()["attempts"] == 0
    assert client.get("/progress", params=params).status_code == 401
    assert client.get("/progress", params={"date_from": "invalid"}, headers=owner).status_code == 422


def test_date_window_boundaries_empty_days_and_weighted_phonemes():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(email="window@example.test", password_hash="unused")
        other = User(email="other@example.test", password_hash="unused")
        db.add_all([user, other])
        db.flush()
        def add(owner, timestamp, score):
            assessment = Assessment.model_validate({"sentence_score": score, "words": [{
                "word": "think", "score": score,
                "phonemes": [{"ipa": "θ", "score": score, "start": 0, "end": 1}],
            }]})
            db.add(Attempt(user_id=owner.id, text="think", sentence_score=score,
                           detail_json=assessment.model_dump_json(), created_at=timestamp))
        add(user, datetime(2026, 1, 1, 16, 59, 59), 100)
        add(user, datetime(2026, 1, 1, 17), 20)
        add(user, datetime(2026, 1, 2, 16, 59, 59), 60)
        add(user, datetime(2026, 1, 2, 17), 90)
        add(other, datetime(2026, 1, 2, 10), 0)
        add(user, datetime.now(timezone.utc).replace(tzinfo=None), 80)
        db.commit()
        result = get_progress(user, db, "Asia/Ho_Chi_Minh", date(2026, 1, 2), date(2026, 1, 2))
        assert result.attempts == 2 and result.daily[0]["sentence_average"] == 40
        assert result.weak_phonemes == [{"ipa": "θ", "average": 40, "samples": 2}]
        assert result.streak_days == get_progress(user, db).streak_days
        empty = get_progress(user, db, "UTC", date(2020, 1, 1), date(2020, 1, 2))
        assert empty.attempts == 0 and empty.weak_phonemes == []
        assert len(empty.daily) == 2 and all(row["sentence_average"] is None for row in empty.daily)
        for start, end in ((date(2026, 1, 1), None), (date(2026, 1, 2), date(2026, 1, 1)),
                           (date(2020, 1, 1), date(2026, 1, 1)), (date.max, date.max)):
            with pytest.raises(HTTPException) as error:
                get_progress(user, db, "UTC", start, end)
            assert error.value.status_code == 422
        with pytest.raises(HTTPException) as error:
            get_progress(user, db, "Asia/Ho_Chi_Minh", date.min, date.min)
        assert error.value.status_code == 422
    engine.dispose()
