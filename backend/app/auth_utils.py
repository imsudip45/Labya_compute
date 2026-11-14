"""Password hashing, JWTs, and the dependencies that resolve the current user."""
import uuid
from datetime import timedelta
from typing import Literal, Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session, select

from app.config import settings
from app.db import get_session
from app.models import Host, Renter, User, utcnow

ALGORITHM = "HS256"
_bearer = HTTPBearer(auto_error=False)
# Compared against when the email is unknown, so a failed login takes the same time either way.
_DUMMY_HASH = bcrypt.hashpw(b"timing-equaliser", bcrypt.gensalt()).decode()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(password: str, hashed: Optional[str]) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), (hashed or _DUMMY_HASH).encode()) and hashed is not None
    except ValueError:
        return False


def _token(user: User, kind: Literal["access", "refresh"], lifetime: timedelta) -> str:
    now = utcnow()
    claims = {"sub": str(user.id), "type": kind, "ver": user.token_version, "iat": now, "exp": now + lifetime}
    return jwt.encode(claims, settings.secret_key, algorithm=ALGORITHM)


def issue_tokens(user: User) -> dict:
    return {
        "access": _token(user, "access", timedelta(minutes=settings.access_token_expire_minutes)),
        "refresh": _token(user, "refresh", timedelta(days=settings.refresh_token_expire_days)),
    }


def user_from_token(token: str, kind: Literal["access", "refresh"], db: Session) -> User:
    """Decode a token of the given kind and return its still-valid user, or raise 401."""
    denied = HTTPException(status.HTTP_401_UNAUTHORIZED, "Your login has expired. Log in again.", {"WWW-Authenticate": "Bearer"})
    try:
        claims = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM], options={"require": ["exp", "sub", "type"]})
        user_id = uuid.UUID(claims["sub"])
    except (jwt.PyJWTError, ValueError):
        raise denied
    if claims["type"] != kind:
        raise denied
    user = db.get(User, user_id)
    if not user or claims.get("ver") != user.token_version:
        raise denied
    return user


def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer), db: Session = Depends(get_session)
) -> User:
    if not creds:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Log in to continue.", {"WWW-Authenticate": "Bearer"})
    return user_from_token(creds.credentials, "access", db)


def get_current_renter(user: User = Depends(get_current_user), db: Session = Depends(get_session)) -> Renter:
    renter = db.exec(select(Renter).where(Renter.user_id == user.id)).first()
    if not renter:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only renter accounts can do this.")
    return renter


def get_current_host(user: User = Depends(get_current_user), db: Session = Depends(get_session)) -> Host:
    host = db.exec(select(Host).where(Host.user_id == user.id)).first()
    if not host:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only host accounts can do this.")
    return host
