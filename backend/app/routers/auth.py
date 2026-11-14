from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.auth_utils import get_current_user, hash_password, issue_tokens, user_from_token, verify_password
from app.config import settings
from app.db import get_session
from app.models import Host, Renter, User, Wallet, utcnow
from app.schemas import LoginPayload, MeResponse, RefreshPayload, RegisterPayload, TokenResponse

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def _register(payload: RegisterPayload, role: type[Renter] | type[Host], db: Session) -> TokenResponse:
    email = payload.email.lower()
    if db.exec(select(User).where(User.email == email)).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "User already exists")
    user = User(email=email, hashed_password=hash_password(payload.password), first_name=payload.name)
    profile = role(user_id=user.id)
    wallet = Wallet(renter_id=profile.id) if role is Renter else Wallet(host_id=profile.id)
    db.add(user)
    db.flush()
    db.add(profile)
    db.flush()
    db.add(wallet)
    try:
        db.commit()
    except IntegrityError:  # same email registered concurrently
        db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "User already exists")
    return TokenResponse(**issue_tokens(user))


@router.post("/register/renter/", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register_renter(payload: RegisterPayload, db: Session = Depends(get_session)):
    return _register(payload, Renter, db)


@router.post("/register/host/", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register_host(payload: RegisterPayload, db: Session = Depends(get_session)):
    return _register(payload, Host, db)


@router.post("/login/", response_model=TokenResponse)
def login(payload: LoginPayload, db: Session = Depends(get_session)):
    user = db.exec(select(User).where(User.email == payload.email.lower()).with_for_update()).first()
    now = utcnow()
    if user and user.locked_until and user.locked_until > now:
        minutes = int((user.locked_until - now).total_seconds() // 60) + 1
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, f"Too many failed attempts. Try again in {minutes} min.")
    if not verify_password(payload.password, user.hashed_password if user else None):
        if user:
            user.failed_logins += 1
            if user.failed_logins >= settings.max_failed_logins:
                user.failed_logins = 0
                user.locked_until = now + timedelta(minutes=settings.login_lockout_minutes)
            db.add(user)
            db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    if user.failed_logins or user.locked_until:
        user.failed_logins, user.locked_until = 0, None
        db.add(user)
        db.commit()
    return TokenResponse(**issue_tokens(user))


@router.post("/refresh/", response_model=TokenResponse)
def refresh(body: RefreshPayload, db: Session = Depends(get_session)):
    return TokenResponse(**issue_tokens(user_from_token(body.refresh, "refresh", db)))


@router.post("/logout/", status_code=status.HTTP_204_NO_CONTENT)
def logout(user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    """Revoke every access and refresh token this user holds, on all devices."""
    user.token_version += 1
    db.add(user)
    db.commit()


@router.get("/me/", response_model=MeResponse)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    host = db.exec(select(Host).where(Host.user_id == user.id)).first()
    renter = None if host else db.exec(select(Renter).where(Renter.user_id == user.id)).first()
    return MeResponse(
        id=user.id, email=user.email, first_name=user.first_name, last_name=user.last_name,
        role="HOST" if host else "RENTER" if renter else None,
        profile_id=host.id if host else renter.id if renter else None,
    )
