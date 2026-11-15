"""Summarize completed learning outcomes still present in the learner's history."""
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, literal, or_, select, union_all

from .auth import CurrentUser, DB
from .models import Attempt, Card, DialogueTurn, Review, Session, StudySession

router = APIRouter()


class ActivityCounts(BaseModel):
    pronunciation: int = 0
    talk: int = 0
    reviews: int = 0
    total: int = 0


class DailyActivity(ActivityCounts):
    date: date


class DailyGoal(BaseModel):
    date: date
    target: int
    completed: int
    remaining: int
    achieved: bool
    activities: ActivityCounts


class DashboardView(BaseModel):
    timezone: str
    date_from: date
    date_to: date
    daily: list[DailyActivity]
    totals: ActivityCounts
    today: DailyGoal
    due_cards: int
    active_study_session_id: int | None
    undated_talk_turns: int


def utc_window(first: date, last: date, zone: ZoneInfo) -> tuple[datetime, datetime]:
    if last < first or (last - first).days > 365 or last == date.max:
        raise HTTPException(422, "Date range must contain 1 to 366 days")
    try:
        start = datetime.combine(first, datetime.min.time(), tzinfo=zone)
        end = datetime.combine(last + timedelta(days=1), datetime.min.time(), tzinfo=zone)
        return (start.astimezone(timezone.utc).replace(tzinfo=None),
                end.astimezone(timezone.utc).replace(tzinfo=None))
    except (OverflowError, ValueError):
        raise HTTPException(422, "Date range outside supported timestamps") from None


@router.get("/dashboard")
def get_dashboard(
    user: CurrentUser, db: DB, timezone_name: str | None = None,
    date_from: date | None = None, date_to: date | None = None,
) -> DashboardView:
    timezone_name = timezone_name or user.timezone_name
    try:
        zone = ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError):
        raise HTTPException(422, "Unknown timezone") from None
    now = datetime.now(timezone.utc)
    today = now.astimezone(zone).date()
    if (date_from is None) != (date_to is None):
        raise HTTPException(422, "Provide both date_from and date_to")
    if date_from is None:
        date_from, date_to = today - timedelta(days=29), today
    start, end = utc_window(date_from, date_to, zone)
    today_start, today_end = utc_window(today, today, zone)

    def in_window(column):
        return or_((column >= start) & (column < end),
                   (column >= today_start) & (column < today_end))

    # Count persisted outcomes, not request receipts; replay cannot add activity.
    query = union_all(
        select(Attempt.created_at, literal("pronunciation")).where(
            Attempt.user_id == user.id, in_window(Attempt.created_at)),
        select(DialogueTurn.completed_at, literal("talk")).join(
            Session, Session.id == DialogueTurn.session_id).where(
            Session.user_id == user.id, in_window(DialogueTurn.completed_at)),
        select(Review.reviewed_at, literal("reviews")).join(
            Card, Card.id == Review.card_id).where(
            Card.user_id == user.id, in_window(Review.reviewed_at)),
    )
    daily = {date_from + timedelta(days=i): DailyActivity(date=date_from + timedelta(days=i))
             for i in range((date_to - date_from).days + 1)}
    totals, today_counts = ActivityCounts(), ActivityCounts()
    for timestamp, kind in db.execute(query.execution_options(yield_per=100)):
        day = timestamp.replace(tzinfo=timezone.utc).astimezone(zone).date()
        targets = []
        if day in daily:
            targets.extend((daily[day], totals))
        if day == today:
            targets.append(today_counts)
        for target in targets:
            setattr(target, kind, getattr(target, kind) + 1)
            target.total += 1

    due_cards = db.scalar(select(func.count()).select_from(Card).where(
        Card.user_id == user.id, Card.suspended.is_(False),
        Card.due <= now.replace(tzinfo=None)))
    active = db.scalar(select(StudySession.id).where(
        StudySession.user_id == user.id, StudySession.status == "active"))
    undated = db.scalar(select(func.count()).select_from(DialogueTurn).join(
        Session, Session.id == DialogueTurn.session_id).where(
        Session.user_id == user.id, DialogueTurn.completed_at.is_(None)))
    return DashboardView(
        timezone=timezone_name, date_from=date_from, date_to=date_to,
        daily=list(daily.values()), totals=totals,
        today=DailyGoal(date=today, target=user.daily_goal, completed=today_counts.total,
                       remaining=max(0, user.daily_goal - today_counts.total),
                       achieved=today_counts.total >= user.daily_goal, activities=today_counts),
        due_cards=due_cards, active_study_session_id=active, undated_talk_turns=undated,
    )
