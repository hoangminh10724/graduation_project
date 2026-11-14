from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, func, false
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class RateLimit(Base):
    __tablename__ = "rate_limits"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    window_start: Mapped[datetime] = mapped_column(DateTime, index=True)
    hits: Mapped[int] = mapped_column(Integer)


class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    topic: Mapped[str] = mapped_column(String(120), default="")
    cefr_level: Mapped[str] = mapped_column(String(2), default="A2")
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    busy_until: Mapped[datetime | None] = mapped_column(DateTime)
    turn_token: Mapped[str | None] = mapped_column(String(36))


class Deck(Base):
    __tablename__ = "decks"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(String(1000), default="")


class Card(Base):
    """Thẻ ôn tập FSRS."""
    __tablename__ = "cards"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    front: Mapped[str] = mapped_column(Text)
    back: Mapped[str] = mapped_column(Text)
    stability: Mapped[float] = mapped_column(Float, default=0.0)
    difficulty: Mapped[float] = mapped_column(Float, default=0.0)
    due: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    deck_id: Mapped[int | None] = mapped_column(ForeignKey("decks.id", ondelete="SET NULL"))
    suspended: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    __table_args__ = (Index("ix_cards_user_due", "user_id", "suspended", "due", "id"),)


class DialogueTurn(Base):
    __tablename__ = "dialogue_turns"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), index=True)
    learner_text: Mapped[str] = mapped_column(Text)
    tutor_text: Mapped[str] = mapped_column(Text)


class Review(Base):
    __tablename__ = "reviews"
    id: Mapped[int] = mapped_column(primary_key=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id"))
    rating: Mapped[int] = mapped_column(Integer)  # 1 Again, 2 Hard, 3 Good, 4 Easy
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    request_id: Mapped[str | None] = mapped_column(String(36), unique=True)
    result_json: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (Index("ix_reviews_card_time", "card_id", "reviewed_at"),)


class Attempt(Base):
    """Một lần luyện phát âm."""
    __tablename__ = "attempts"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    text: Mapped[str] = mapped_column(Text)
    sentence_score: Mapped[float] = mapped_column(Float)
    detail_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
