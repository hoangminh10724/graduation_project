from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func, false, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"sqlite_autoincrement": True}
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    display_name: Mapped[str] = mapped_column(String(120), server_default="")
    timezone_name: Mapped[str] = mapped_column(String(80), server_default="Asia/Ho_Chi_Minh")
    cefr_level: Mapped[str] = mapped_column(String(2), server_default="A2")
    daily_goal: Mapped[int] = mapped_column(Integer, server_default="10")
    token_version: Mapped[int] = mapped_column(Integer, server_default="0")
    email_verified: Mapped[bool] = mapped_column(Boolean, server_default=false())


class AccountAction(Base):
    __tablename__ = "account_actions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    purpose: Mapped[str] = mapped_column(String(20))
    token_digest: Mapped[str] = mapped_column(String(64), unique=True)
    token_version: Mapped[int] = mapped_column(Integer)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    consumed: Mapped[bool] = mapped_column(Boolean, server_default=false())
    delivery_status: Mapped[str] = mapped_column(String(12))
    delivery_attempts: Mapped[int] = mapped_column(Integer, server_default="0")
    available_at: Mapped[datetime] = mapped_column(DateTime)
    lease_token: Mapped[str | None] = mapped_column(String(36))
    lease_until: Mapped[datetime | None] = mapped_column(DateTime)
    __table_args__ = (
        Index("ix_account_actions_user_purpose", "user_id", "purpose"),
        Index("ix_account_actions_delivery", "delivery_status", "available_at"),
    )


class LoginSession(Base):
    __tablename__ = "login_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    refresh_digest: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    revoked: Mapped[bool] = mapped_column(Boolean, server_default=false())


class UsedRefresh(Base):
    __tablename__ = "used_refresh_tokens"
    digest: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("login_sessions.id"), index=True)


class RateLimit(Base):
    __tablename__ = "rate_limits"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    window_start: Mapped[datetime] = mapped_column(DateTime, index=True)
    hits: Mapped[int] = mapped_column(Integer)


class AIRequest(Base):
    __tablename__ = "ai_requests"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    session_id: Mapped[int | None] = mapped_column(ForeignKey("sessions.id", ondelete="SET NULL"), index=True)
    request_id: Mapped[str] = mapped_column(String(36))
    kind: Mapped[str] = mapped_column(String(10))
    fingerprint: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(12))
    events_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    deadline: Mapped[datetime] = mapped_column(DateTime)
    turn_token: Mapped[str | None] = mapped_column(String(36))
    __table_args__ = (UniqueConstraint("user_id", "request_id", name="uq_ai_requests_user_request"),
                      {"sqlite_autoincrement": True})


class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    topic: Mapped[str] = mapped_column(String(120), default="")
    title: Mapped[str] = mapped_column(String(120), server_default="")
    cefr_level: Mapped[str] = mapped_column(String(2), default="A2")
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    busy_until: Mapped[datetime | None] = mapped_column(DateTime)
    turn_token: Mapped[str | None] = mapped_column(String(36))
    __table_args__ = (Index("ix_sessions_user_id_id", "user_id", "id"), {"sqlite_autoincrement": True})


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
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)


class Review(Base):
    __tablename__ = "reviews"
    id: Mapped[int] = mapped_column(primary_key=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id"))
    rating: Mapped[int] = mapped_column(Integer)  # 1 Again, 2 Hard, 3 Good, 4 Easy
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    request_id: Mapped[str | None] = mapped_column(String(36), unique=True)
    result_json: Mapped[str | None] = mapped_column(Text)
    study_session_id: Mapped[int | None] = mapped_column(ForeignKey("study_sessions.id"), index=True)
    __table_args__ = (Index("ix_reviews_card_time", "card_id", "reviewed_at"),)


class StudySession(Base):
    __tablename__ = "study_sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    request_id: Mapped[str] = mapped_column(String(36))
    selection_json: Mapped[str] = mapped_column(Text)
    deck_id: Mapped[int | None] = mapped_column(ForeignKey("decks.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(12))
    started_at: Mapped[datetime] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    __table_args__ = (
        UniqueConstraint("user_id", "request_id", name="uq_study_user_request"),
        Index("ix_study_user_id", "user_id", "id"),
        Index("uq_study_active_user", "user_id", unique=True,
              postgresql_where=text("status = 'active'"), sqlite_where=text("status = 'active'")),
    )


class StudyItem(Base):
    __tablename__ = "study_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    study_session_id: Mapped[int] = mapped_column(ForeignKey("study_sessions.id"))
    card_id: Mapped[int | None] = mapped_column(ForeignKey("cards.id", ondelete="SET NULL"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    expected_due: Mapped[datetime] = mapped_column(DateTime)
    state: Mapped[str] = mapped_column(String(12))
    skip_reason: Mapped[str | None] = mapped_column(String(30))
    rating: Mapped[int | None] = mapped_column(Integer)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)
    __table_args__ = (UniqueConstraint("study_session_id", "card_id", name="uq_study_item_card"),)


class Attempt(Base):
    """Một lần luyện phát âm."""
    __tablename__ = "attempts"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    text: Mapped[str] = mapped_column(Text)
    reference_text: Mapped[str | None] = mapped_column(Text)
    transcript: Mapped[str | None] = mapped_column(Text)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("sessions.id", ondelete="SET NULL"))
    sentence_score: Mapped[float] = mapped_column(Float)
    detail_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    __table_args__ = (Index("ix_attempts_user_id_id", "user_id", "id"),)
