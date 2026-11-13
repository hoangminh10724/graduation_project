from datetime import datetime, timedelta, timezone

import pytest

from app.fsrs import Card, Rating, retrievability, review


NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


# Values generated with py-fsrs 5.1.3, empty learning/relearning steps and fuzzing off.
@pytest.mark.parametrize(
    ("rating", "stability", "difficulty", "days"),
    [
        (Rating.AGAIN, 0.40255, 7.1949, 1),
        (Rating.HARD, 1.18385, 6.4883052685, 1),
        (Rating.GOOD, 3.173, 5.2824344223, 3),
        (Rating.EASY, 15.69105, 3.2245015894, 16),
    ],
)
def test_first_review(rating, stability, difficulty, days):
    card = Card(due=NOW)
    updated, interval = review(card, rating, NOW)

    assert card.state == "new"
    assert updated.state == "review"
    assert updated.stability == pytest.approx(stability)
    assert updated.difficulty == pytest.approx(difficulty)
    assert updated.last_review == NOW
    assert interval == timedelta(days=days)
    assert updated.due == NOW + interval


@pytest.mark.parametrize(
    ("elapsed", "stabilities", "days"),
    [
        (0, (5.0102852419, 8.3984137438, 14.0777121474, 23.5975489360), (5, 8, 14, 24)),
        (10, (2.1076962577, 15.3139121143, 32.9542639925, 78.6286584846), (2, 15, 33, 79)),
    ],
)
def test_existing_card(elapsed, stabilities, days):
    card = Card(NOW, 10.0, 5.0, NOW - timedelta(days=elapsed, hours=3))
    outcomes = [review(card, rating, NOW) for rating in Rating]

    assert [updated.stability for updated, _ in outcomes] == pytest.approx(stabilities)
    assert [updated.difficulty for updated, _ in outcomes] == pytest.approx(
        [6.6070351073, 5.7994339073, 4.9918327073, 4.1842315073]
    )
    assert [interval.days for _, interval in outcomes] == list(days)
    assert outcomes[0][0].stability < card.stability
    assert all(updated.due == NOW + interval for updated, interval in outcomes)
    assert card.stability == 10.0


def test_retrievability_declines_with_elapsed_time():
    assert retrievability(0, 10) == 1
    assert retrievability(10, 10) == pytest.approx(0.9)
    assert retrievability(20, 10) < 0.9


@pytest.mark.parametrize("rating", [0, 5, True, 2.0])
def test_rejects_invalid_rating(rating):
    with pytest.raises(ValueError, match="rating"):
        review(Card(due=NOW), rating, NOW)


def test_rejects_backdated_review():
    card, _ = review(Card(due=NOW), Rating.GOOD, NOW)
    with pytest.raises(ValueError, match="last_review"):
        review(card, Rating.EASY, NOW - timedelta(seconds=1))
