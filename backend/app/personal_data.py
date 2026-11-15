"""Authenticated learning-data downloads with explicit field allowlists."""
import json
from datetime import datetime, timezone
from tempfile import SpooledTemporaryFile

import bcrypt
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, SecretStr, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from .auth import CurrentUser, DB, unauthorized
from .limits import enforce_limit
from .models import Attempt, Card, Deck, DialogueTurn, Review, Session, StudyItem, StudySession, User

router = APIRouter(prefix="/me")
MAX_EXPORT_BYTES = 50 * 1024 * 1024


class ConfirmPassword(BaseModel):
    current_password: SecretStr

    @field_validator("current_password")
    @classmethod
    def validate_password(cls, value: SecretStr) -> SecretStr:
        if not 1 <= len(value.get_secret_value().encode()) <= 72:
            raise ValueError("Password must contain 1 to 72 bytes")
        return value


class ExportResponse(StreamingResponse):
    def __init__(self, file):
        self.file = file
        size = file.tell()
        file.seek(0)
        super().__init__(iter(lambda: file.read(64 * 1024), b""), media_type="application/json",
                         headers={"Content-Disposition": 'attachment; filename="wordspeak-data.json"',
                                  "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
                                  "Content-Length": str(size)})

    async def __call__(self, scope, receive, send):
        try:
            await super().__call__(scope, receive, send)
        finally:
            self.file.close()


def json_value(value):
    if isinstance(value, datetime):
        return value.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
    raise TypeError(f"Unsupported export value: {type(value).__name__}")


def export_queries(user_id: int):
    def columns(model, names):
        return [getattr(model, name) for name in names.split()]

    # Do not serialize ORM __dict__ or auth/queue/request tables: future secret
    # fields must never silently become downloadable.
    yield "decks", select(*columns(Deck, "id name description")).where(Deck.user_id == user_id).order_by(Deck.id)
    yield "cards", select(*columns(Card, "id deck_id front back stability difficulty due suspended")).where(Card.user_id == user_id).order_by(Card.id)
    yield "reviews", select(*columns(Review, "id card_id rating reviewed_at request_id study_session_id")).join(Card, Card.id == Review.card_id).where(Card.user_id == user_id).order_by(Review.id)
    yield "talk_sessions", select(*columns(Session, "id title topic cefr_level started_at")).where(Session.user_id == user_id).order_by(Session.id)
    yield "talk_turns", select(*columns(DialogueTurn, "id session_id learner_text tutor_text completed_at")).join(Session, Session.id == DialogueTurn.session_id).where(Session.user_id == user_id).order_by(DialogueTurn.id)
    yield "pronunciation_attempts", select(*columns(Attempt, "id text reference_text transcript session_id sentence_score detail_json created_at")).where(Attempt.user_id == user_id).order_by(Attempt.id)
    yield "study_sessions", select(*columns(StudySession, "id deck_id status started_at finished_at request_id selection_json")).where(StudySession.user_id == user_id).order_by(StudySession.id)
    yield "study_items", select(*columns(StudyItem, "id study_session_id card_id position expected_due state skip_reason rating reviewed_at")).join(StudySession, StudySession.id == StudyItem.study_session_id).where(StudySession.user_id == user_id).order_by(StudyItem.id)


def build_export(snapshot: DBSession, user: User):
    file = SpooledTemporaryFile(max_size=1024 * 1024, mode="w+b")

    def write(value):
        data = value.encode("utf-8")
        if file.tell() + len(data) > MAX_EXPORT_BYTES:
            raise HTTPException(413, "Learning data export exceeds 50 MiB")
        file.write(data)

    def encode(value):
        return json.dumps(value, ensure_ascii=False, default=json_value, allow_nan=False)

    try:
        profile = {name: getattr(user, name) for name in (
            "id", "email", "created_at", "email_verified", "display_name", "timezone_name", "cefr_level", "daily_goal")}
        metadata = {"schema_version": 1, "exported_at": datetime.now(timezone.utc), "profile": profile}
        write(encode(metadata)[:-1])
        for name, query in export_queries(user.id):
            write("," + encode(name) + ":[")
            first = True
            for row in snapshot.execute(query.execution_options(yield_per=100)).mappings():
                if not first:
                    write(",")
                write(encode(dict(row)))
                first = False
            write("]")
        write("}")
        return file
    except BaseException:
        file.close()
        raise


@router.post("/export", response_class=StreamingResponse,
             responses={200: {"content": {"application/json": {"schema": {"type": "object"}}},
                              "description": "Versioned learning-data JSON attachment"},
                        401: {"description": "Invalid access token or password"},
                        413: {"description": "Export exceeds 50 MiB"},
                        429: {"description": "Export request limit exceeded"}})
def export_data(payload: ConfirmPassword, user: CurrentUser, db: DB):
    user_id, version = user.id, user.token_version
    enforce_limit(db, "personal-export", str(user_id), 3)
    bind = db.get_bind()
    # Materialize before sending headers so failures never return a truncated
    # success response. The read snapshot ends before a slow download begins.
    file = None
    try:
        with bind.connect() as connection:
            if connection.dialect.name == "postgresql":
                connection = connection.execution_options(isolation_level="REPEATABLE READ")
            else:
                connection.exec_driver_sql("BEGIN")
            with DBSession(bind=connection) as snapshot:
                owner = snapshot.get(User, user_id)
                if owner is None or owner.token_version != version or not bcrypt.checkpw(
                    payload.current_password.get_secret_value().encode(), owner.password_hash.encode()
                ):
                    raise unauthorized()
                file = build_export(snapshot, owner)
        return ExportResponse(file)
    except BaseException:
        if file is not None:
            file.close()
        raise
