from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlmodel import Session, select
from app.config import settings
from app.db import get_session
from app.models import User, Renter, Host

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login/", auto_error=False)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)

def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)

def get_current_user(token: Optional[str] = Depends(oauth2_scheme), db: Session = Depends(get_session)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        # Fallback: check Authorization header manually if OAuth2PasswordBearer failed
        raise credentials_exception
    try:
        # Support both 'Bearer <token>' and raw token if header extraction was manual
        if token.startswith("Bearer "):
            token = token.split(" ")[1]
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    statement = select(User).where(User.email == email)
    user = db.exec(statement).first()
    if user is None:
        raise credentials_exception
    return user

def get_current_renter(user: User = Depends(get_current_user), db: Session = Depends(get_session)) -> Renter:
    statement = select(Renter).where(Renter.user_id == user.id)
    renter = db.exec(statement).first()
    if not renter:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Renter role required")
    return renter

def get_current_host(user: User = Depends(get_current_user), db: Session = Depends(get_session)) -> Host:
    statement = select(Host).where(Host.user_id == user.id)
    host = db.exec(statement).first()
    if not host:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Host role required")
    return host
