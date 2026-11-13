"""FSRS-5 memory model with deterministic, whole-day review intervals."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import IntEnum
from math import exp, expm1, isfinite, log1p


# FSRS-5 default parameters from the Open Spaced Repetition algorithm wiki.
_WEIGHTS = (
    0.40255, 1.18385, 3.173, 15.69105, 7.1949, 0.5345, 1.4604, 0.0046,
    1.54575, 0.1192, 1.01925, 1.9395, 0.11, 0.29605, 2.2698, 0.2315,
    2.9898, 0.51655, 0.6621,
)
_TARGET_RETENTION = 0.9
_DECAY = -0.5
_FACTOR = _TARGET_RETENTION ** (1 / _DECAY) - 1
_MAX_INTERVAL_DAYS = 36500


class Rating(IntEnum):
    AGAIN = 1
    HARD = 2
    GOOD = 3
    EASY = 4


@dataclass(frozen=True)
class Card:
    due: datetime
    stability: float = 0.0
    difficulty: float = 0.0
    last_review: datetime | None = None

    @property
    def state(self) -> str:
        return "new" if self.last_review is None else "review"


def retrievability(elapsed_days: float, stability: float) -> float:
    """Estimate recall probability given the time since review and stability in days."""
    if not isfinite(elapsed_days) or elapsed_days < 0:
        raise ValueError("elapsed_days must be finite and nonnegative")
    if not isfinite(stability) or stability <= 0:
        raise ValueError("stability must be finite and positive")
    return (1 + _FACTOR * elapsed_days / stability) ** _DECAY


def _clamp_difficulty(difficulty: float) -> float:
    return min(10.0, max(1.0, difficulty))


def _initial_difficulty(rating: Rating) -> float:
    return _clamp_difficulty(_WEIGHTS[4] - expm1(_WEIGHTS[5] * (rating - 1)))


def _next_stability(card: Card, rating: Rating, elapsed_days: int) -> float:
    stability, difficulty = card.stability, card.difficulty
    if elapsed_days == 0:
        return stability * exp(_WEIGHTS[17] * (rating - Rating.GOOD + _WEIGHTS[18]))

    forgetting = 1 - retrievability(elapsed_days, stability)
    if rating == Rating.AGAIN:
        lapse_stability = (
            _WEIGHTS[11] * difficulty ** -_WEIGHTS[12]
            * expm1(_WEIGHTS[13] * log1p(stability))
            * exp(_WEIGHTS[14] * forgetting)
        )
        return min(lapse_stability, stability / exp(_WEIGHTS[17] * _WEIGHTS[18]))

    hard_penalty = _WEIGHTS[15] if rating == Rating.HARD else 1.0
    easy_bonus = _WEIGHTS[16] if rating == Rating.EASY else 1.0
    gain = (
        exp(_WEIGHTS[8]) * (11 - difficulty) * stability ** -_WEIGHTS[9]
        * expm1(_WEIGHTS[10] * forgetting) * hard_penalty * easy_bonus
    )
    return stability * (1 + gain)


def review(card: Card, rating: int, now: datetime) -> tuple[Card, timedelta]:
    """Return the updated card and interval using timezone-aware review timestamps."""
    if not isinstance(rating, int) or isinstance(rating, bool) or not 1 <= rating <= 4:
        raise ValueError("rating must be an integer from 1 to 4")
    grade = Rating(rating)
    if now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    now = now.astimezone(timezone.utc)

    if card.last_review is None:
        stability = _WEIGHTS[grade - 1]
        difficulty = _initial_difficulty(grade)
    else:
        if card.last_review.utcoffset() is None or now < card.last_review:
            raise ValueError("last_review must be timezone-aware and no later than now")
        if not isfinite(card.stability) or card.stability <= 0:
            raise ValueError("stability must be finite and positive")
        if not 1 <= card.difficulty <= 10:
            raise ValueError("difficulty must be between 1 and 10")

        elapsed_days = (now - card.last_review).days
        stability = _next_stability(card, grade, elapsed_days)
        delta = -_WEIGHTS[6] * (grade - Rating.GOOD)
        damped = card.difficulty + delta * (10 - card.difficulty) / 9
        difficulty = _clamp_difficulty(
            _WEIGHTS[7] * _initial_difficulty(Rating.EASY) + (1 - _WEIGHTS[7]) * damped
        )

    # At 90% retention, the FSRS-5 interval in days equals stability.
    interval = timedelta(days=max(1, round(min(stability, _MAX_INTERVAL_DAYS))))
    return Card(now + interval, stability, difficulty, last_review=now), interval
