import os
import secrets
from hashlib import sha256
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from typing import Annotated

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .db import get_db
from .models import LoginSession, UsedRefresh, User
from .limits import client_ip, enforce_limit

router = APIRouter(prefix="/auth")
DB = Annotated[Session, Depends(get_db)]
bearer = HTTPBearer(auto_error=False)
_DUMMY_HASH = bcrypt.hashpw(b"unavailable account", bcrypt.gensalt())


class Credentials(BaseModel):
    email: str = Field(max_length=255, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    password: str = Field(min_length=8)

    @field_validator("password")
    @classmethod
    def check_password_bytes(cls, password: str) -> str:
        if len(password.encode()) > 72:
            raise ValueError("password must be at most 72 bytes")
        return password


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str
    expires_in: int = 900
    session_id: str


def jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET", "")
    if len(secret.encode()) < 32:
        raise HTTPException(503, "JWT_SECRET must contain at least 32 bytes")
    return secret


def issue_token(db: Session, user: User, secret: str, login_session: LoginSession | None = None) -> Token:
    now = datetime.now(timezone.utc)
    refresh = secrets.token_urlsafe(48)
    digest = sha256(refresh.encode()).hexdigest()
    if login_session is None:
        login_session = LoginSession(
            id=str(uuid4()), user_id=user.id, refresh_digest=digest,
            created_at=now.replace(tzinfo=None),
            expires_at=(now + timedelta(days=30)).replace(tzinfo=None), revoked=False,
        )
        db.add(login_session)
    else:
        db.add(UsedRefresh(digest=login_session.refresh_digest, session_id=login_session.id))
        login_session.refresh_digest = digest
    claims = {
        "sub": str(user.id), "iat": now, "exp": now + timedelta(minutes=15),
        "sid": login_session.id, "ver": user.token_version,
    }
    return Token(
        access_token=jwt.encode(claims, secret, algorithm="HS256"),
        refresh_token=refresh, session_id=login_session.id,
    )


def unauthorized() -> HTTPException:
    return HTTPException(401, "Invalid credentials", headers={"WWW-Authenticate": "Bearer"})


def current_user(
    db: DB, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]
) -> User:
    if credentials is None:
        raise unauthorized()
    return user_from_token(db, credentials.credentials)


def user_from_token(db: Session, token: str) -> User:
    try:
        claims = jwt.decode(
            token, jwt_secret(), algorithms=["HS256"],
            options={"require": ["exp", "sub"]},
        )
        user_id = int(claims["sub"])
    except (jwt.InvalidTokenError, ValueError):
        raise unauthorized() from None
    user = db.get(User, user_id)
    if user is None:
        raise unauthorized()
    if claims.get("ver", 0) != user.token_version:
        raise unauthorized()
    session_id = claims.get("sid")
    if session_id is not None:
        session = db.get(LoginSession, session_id)
        if (
            session is None or session.user_id != user.id or session.revoked
            or session.expires_at <= datetime.now(timezone.utc).replace(tzinfo=None)
        ):
            raise unauthorized()
    return user


CurrentUser = Annotated[User, Depends(current_user)]


@router.post("/register", status_code=201)
def register(credentials: Credentials, db: DB, request: Request) -> Token:
    enforce_limit(db, "register", client_ip(request), 5)
    secret = jwt_secret()
    user = User(
        email=credentials.email.lower(),
        password_hash=bcrypt.hashpw(credentials.password.encode(), bcrypt.gensalt()).decode(),
    )
    db.add(user)
    try:
        db.flush()
        token = issue_token(db, user, secret)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Email already registered") from None
    return token


@router.post("/login")
def login(credentials: Credentials, db: DB, request: Request) -> Token:
    enforce_limit(db, "login-ip", client_ip(request), 30)
    enforce_limit(db, "login-email", credentials.email.lower(), 10)
    user = db.scalar(select(User).where(User.email == credentials.email.lower()).with_for_update())
    matches = bcrypt.checkpw(
        credentials.password.encode(), user.password_hash.encode() if user else _DUMMY_HASH
    )
    if user is None or not matches:
        raise unauthorized()
    token = issue_token(db, user, jwt_secret())
    db.commit()
    return token


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=32, max_length=256)


@router.post("/refresh")
def refresh(payload: RefreshRequest, db: DB, request: Request) -> Token:
    enforce_limit(db, "refresh-ip", client_ip(request), 30)
    digest = sha256(payload.refresh_token.encode()).hexdigest()
    session = db.scalar(select(LoginSession).where(LoginSession.refresh_digest == digest))
    if session is None:
        used = db.get(UsedRefresh, digest)
        session = db.get(LoginSession, used.session_id) if used else None
    if session is None:
        raise unauthorized()
    session_id, user_id = session.id, session.user_id
    db.rollback()
    # Consistent lock order with password changes and logout-all.
    user = db.scalar(select(User).where(User.id == user_id).with_for_update())
    session = db.scalar(select(LoginSession).where(LoginSession.id == session_id).with_for_update())
    if user is None or session is None or session.revoked:
        raise unauthorized()
    if session.refresh_digest != digest:
        session.revoked = True
        db.commit()
        raise unauthorized()
    if session.expires_at <= datetime.now(timezone.utc).replace(tzinfo=None):
        session.revoked = True
        db.commit()
        raise unauthorized()
    token = issue_token(db, user, jwt_secret(), session)
    db.commit()
    return token


@router.get("/sessions")
def login_sessions(user: CurrentUser, db: DB) -> list[dict]:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    return [{
        "id": session.id,
        "created_at": session.created_at.replace(tzinfo=timezone.utc),
        "expires_at": session.expires_at.replace(tzinfo=timezone.utc),
    } for session in db.scalars(select(LoginSession).where(
        LoginSession.user_id == user.id, LoginSession.revoked.is_(False),
        LoginSession.expires_at > now,
    ).order_by(LoginSession.created_at.desc()).limit(100))]


@router.delete("/sessions/{session_id}", status_code=204)
def revoke_session(session_id: str, user: CurrentUser, db: DB) -> Response:
    result = db.execute(update(LoginSession).where(
        LoginSession.id == session_id, LoginSession.user_id == user.id
    ).values(revoked=True))
    if result.rowcount != 1:
        raise HTTPException(404, "Login session not found")
    db.commit()
    return Response(status_code=204)


@router.post("/logout-all", status_code=204)
def logout_all(user: CurrentUser, db: DB) -> Response:
    db.execute(update(User).where(User.id == user.id).values(token_version=User.token_version + 1))
    db.execute(update(LoginSession).where(LoginSession.user_id == user.id).values(revoked=True))
    db.commit()
    return Response(status_code=204)


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=72)
    new_password: str = Field(min_length=8)

    @field_validator("current_password", "new_password")
    @classmethod
    def check_bytes(cls, value: str) -> str:
        return Credentials.check_password_bytes(value)


@router.post("/password", status_code=204)
def change_password(payload: PasswordChange, user: CurrentUser, db: DB) -> Response:
    user_id = user.id
    enforce_limit(db, "password", str(user_id), 5)
    locked = db.scalar(select(User).where(User.id == user_id).with_for_update())
    if not bcrypt.checkpw(payload.current_password.encode(), locked.password_hash.encode()):
        raise unauthorized()
    locked.password_hash = bcrypt.hashpw(payload.new_password.encode(), bcrypt.gensalt()).decode()
    locked.token_version += 1
    db.execute(update(LoginSession).where(LoginSession.user_id == user_id).values(revoked=True))
    db.commit()
    return Response(status_code=204)
