import os
from datetime import datetime, timedelta, timezone
from typing import Annotated

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .db import get_db
from .models import User

router = APIRouter(prefix="/auth")
DB = Annotated[Session, Depends(get_db)]
bearer = HTTPBearer(auto_error=False)


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


def jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET", "")
    if len(secret.encode()) < 32:
        raise HTTPException(503, "JWT_SECRET must contain at least 32 bytes")
    return secret


def issue_token(user: User, secret: str) -> Token:
    now = datetime.now(timezone.utc)
    claims = {"sub": str(user.id), "iat": now, "exp": now + timedelta(hours=1)}
    return Token(access_token=jwt.encode(claims, secret, algorithm="HS256"))


def unauthorized() -> HTTPException:
    return HTTPException(401, "Invalid credentials", headers={"WWW-Authenticate": "Bearer"})


def current_user(
    db: DB, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]
) -> User:
    if credentials is None:
        raise unauthorized()
    try:
        claims = jwt.decode(
            credentials.credentials, jwt_secret(), algorithms=["HS256"],
            options={"require": ["exp", "sub"]},
        )
        user_id = int(claims["sub"])
    except (jwt.InvalidTokenError, ValueError):
        raise unauthorized() from None
    user = db.get(User, user_id)
    if user is None:
        raise unauthorized()
    return user


CurrentUser = Annotated[User, Depends(current_user)]


@router.post("/register", status_code=201)
def register(credentials: Credentials, db: DB) -> Token:
    secret = jwt_secret()
    user = User(
        email=credentials.email.lower(),
        password_hash=bcrypt.hashpw(credentials.password.encode(), bcrypt.gensalt()).decode(),
    )
    db.add(user)
    try:
        db.flush()
        token = issue_token(user, secret)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Email already registered") from None
    return token


@router.post("/login")
def login(credentials: Credentials, db: DB) -> Token:
    user = db.scalar(select(User).where(User.email == credentials.email.lower()))
    if user is None or not bcrypt.checkpw(credentials.password.encode(), user.password_hash.encode()):
        raise unauthorized()
    return issue_token(user, jwt_secret())
