from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from app.db import get_session
from app.models import User, Renter, Host, Wallet
from app.schemas import RegisterPayload, LoginPayload, TokenResponse
from app.auth_utils import get_password_hash, verify_password, create_access_token, create_refresh_token

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/register/renter/", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register_renter(payload: RegisterPayload, db: Session = Depends(get_session)):
    stmt = select(User).where(User.email == payload.email)
    existing_user = db.exec(stmt).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")
        
    hashed_pwd = get_password_hash(payload.password)
    user = User(email=payload.email, hashed_password=hashed_pwd, first_name=payload.name)
    db.add(user)
    db.commit()
    db.refresh(user)
    
    renter = Renter(user_id=user.id)
    db.add(renter)
    db.commit()
    db.refresh(renter)
    
    # Create wallet for renter (simulating Django signal)
    wallet = Wallet(renter_id=renter.id)
    db.add(wallet)
    db.commit()
    
    access_token = create_access_token(data={"sub": user.email})
    refresh_token = create_refresh_token(data={"sub": user.email})
    
    return TokenResponse(
        access=access_token,
        refresh=refresh_token,
        message="Renter registered",
        renter_id=renter.id
    )

@router.post("/register/host/", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register_host(payload: RegisterPayload, db: Session = Depends(get_session)):
    stmt = select(User).where(User.email == payload.email)
    existing_user = db.exec(stmt).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")
        
    hashed_pwd = get_password_hash(payload.password)
    user = User(email=payload.email, hashed_password=hashed_pwd, first_name=payload.name)
    db.add(user)
    db.commit()
    db.refresh(user)
    
    host = Host(user_id=user.id)
    db.add(host)
    db.commit()
    db.refresh(host)
    
    # Create wallet for host (simulating Django signal)
    wallet = Wallet(host_id=host.id)
    db.add(wallet)
    db.commit()
    
    access_token = create_access_token(data={"sub": user.email})
    refresh_token = create_refresh_token(data={"sub": user.email})
    
    return TokenResponse(
        access=access_token,
        refresh=refresh_token,
        message="Host registered",
        host_id=host.id
    )

@router.post("/login/", response_model=TokenResponse)
def login(payload: LoginPayload, db: Session = Depends(get_session)):
    stmt = select(User).where(User.email == payload.email)
    user = db.exec(stmt).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
        
    # Find renter/host profile IDs if any
    stmt_renter = select(Renter).where(Renter.user_id == user.id)
    renter = db.exec(stmt_renter).first()
    renter_id = renter.id if renter else None
    
    stmt_host = select(Host).where(Host.user_id == user.id)
    host = db.exec(stmt_host).first()
    host_id = host.id if host else None
    
    access_token = create_access_token(data={"sub": user.email})
    refresh_token = create_refresh_token(data={"sub": user.email})
    
    return TokenResponse(
        access=access_token,
        refresh=refresh_token,
        message="Login successful",
        renter_id=renter_id,
        host_id=host_id
    )

@router.post("/refresh/", response_model=TokenResponse)
def refresh_token_route(refresh: str, db: Session = Depends(get_session)):
    from jose import jwt, JWTError
    from app.config import settings
    try:
        payload = jwt.decode(refresh, settings.secret_key, algorithms=[settings.jwt_algorithm])
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
        
    stmt = select(User).where(User.email == email)
    user = db.exec(stmt).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
        
    access_token = create_access_token(data={"sub": user.email})
    new_refresh = create_refresh_token(data={"sub": user.email})
    
    return TokenResponse(
        access=access_token,
        refresh=new_refresh,
        message="Token refreshed"
    )
