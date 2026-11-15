import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import bcrypt
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, update

from .auth import Credentials, CurrentUser, DB, jwt_secret
from .limits import client_ip, enforce_limit
from .mailer import MailConfigurationError, MailSettings
from .models import AccountAction, LoginSession, User

router = APIRouter(prefix="/auth")


def now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def action_token(action: AccountAction) -> str:
    # Reconstruct for the durable mail queue without storing a usable token in the DB.
    message = f"wordspeak-account-action:{action.id}:{action.user_id}:{action.purpose}:{action.token_version}"
    signature = hmac.new(jwt_secret().encode(), message.encode(), hashlib.sha256).hexdigest()
    return f"{action.id}.{signature}"


def check_mail_configuration() -> None:
    try:
        MailSettings.load()
    except MailConfigurationError:
        raise HTTPException(503, "Email service is not configured") from None
    jwt_secret()


def queue_action(db: DB, user: User, purpose: str) -> None:
    action = AccountAction(
        id=str(uuid4()), user_id=user.id, purpose=purpose, token_version=user.token_version,
        expires_at=now() + (timedelta(minutes=30) if purpose == "reset_password" else timedelta(hours=24)),
        consumed=False, delivery_status="pending", delivery_attempts=0, available_at=now(),
    )
    action.token_digest = hashlib.sha256(action_token(action).encode()).hexdigest()
    db.add(action)


class RecoveryEmail(BaseModel):
    email: str = Field(max_length=255, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class RecoveryAccepted(BaseModel):
    message: str = "If the account is eligible, an email will be sent."


@router.post("/forgot-password", status_code=202)
def forgot_password(payload: RecoveryEmail, db: DB, request: Request) -> RecoveryAccepted:
    enforce_limit(db, "recovery-ip", client_ip(request), 10)
    enforce_limit(db, "recovery-email", payload.email.lower(), 3)
    check_mail_configuration()
    user = db.scalar(select(User).where(User.email == payload.email.lower()).with_for_update())
    if user is not None:
        queue_action(db, user, "reset_password")
    db.commit()
    return RecoveryAccepted()


@router.post("/verification/request", status_code=202)
def request_verification(user: CurrentUser, db: DB) -> RecoveryAccepted:
    user_id = user.id
    enforce_limit(db, "verify-email", str(user_id), 3)
    check_mail_configuration()
    locked = db.scalar(select(User).where(User.id == user_id).with_for_update())
    if locked is not None and not locked.email_verified:
        queue_action(db, locked, "verify_email")
    db.commit()
    return RecoveryAccepted()


class AccountToken(BaseModel):
    token: str = Field(min_length=32, max_length=256)


class PasswordReset(AccountToken):
    new_password: str = Field(min_length=8)

    @field_validator("new_password")
    @classmethod
    def password_bytes(cls, value: str) -> str:
        return Credentials.check_password_bytes(value)


def consume_action(db: DB, raw_token: str, purpose: str) -> User:
    digest = hashlib.sha256(raw_token.encode()).hexdigest()
    action = db.scalar(select(AccountAction).where(AccountAction.token_digest == digest, AccountAction.purpose == purpose))
    if action is None:
        raise HTTPException(400, "Invalid or expired token")
    user_id, action_id = action.user_id, action.id
    db.rollback()
    # Match auth's user -> token/session lock order. The conditional consume also protects SQLite.
    user = db.scalar(select(User).where(User.id == user_id).with_for_update())
    if user is None:
        raise HTTPException(400, "Invalid or expired token")
    accepted = db.execute(update(AccountAction).where(
        AccountAction.id == action_id, AccountAction.consumed.is_(False),
        AccountAction.expires_at > now(), AccountAction.token_version == user.token_version,
    ).values(consumed=True).returning(AccountAction.id)).scalar_one_or_none()
    if accepted is None:
        db.rollback()
        raise HTTPException(400, "Invalid or expired token")
    return user


@router.post("/reset-password", status_code=204)
def reset_password(payload: PasswordReset, db: DB, request: Request) -> Response:
    enforce_limit(db, "reset-consume", client_ip(request), 20)
    password_hash = bcrypt.hashpw(payload.new_password.encode(), bcrypt.gensalt()).decode()
    user = consume_action(db, payload.token, "reset_password")
    user.password_hash = password_hash
    user.token_version += 1
    db.execute(update(LoginSession).where(LoginSession.user_id == user.id).values(revoked=True))
    db.execute(update(AccountAction).where(AccountAction.user_id == user.id).values(consumed=True))
    db.commit()
    return Response(status_code=204)


@router.post("/verify-email", status_code=204)
def verify_email(payload: AccountToken, db: DB, request: Request) -> Response:
    enforce_limit(db, "verify-consume", client_ip(request), 20)
    user = consume_action(db, payload.token, "verify_email")
    user.email_verified = True
    db.execute(update(AccountAction).where(
        AccountAction.user_id == user.id, AccountAction.purpose == "verify_email",
    ).values(consumed=True))
    db.commit()
    return Response(status_code=204)
