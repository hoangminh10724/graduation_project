from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models import Attempt, Base, User
from app.progress import get_progress
from app.speech import Assessment


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
