from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from app.db import get_session
from app.models import Wallet, Transaction, Renter, Host, User
from app.schemas import WalletResponse, WalletDetailResponse, WalletUpdatePayload, TransactionResponse
from app.auth_utils import get_current_user, get_current_renter, get_current_host

router = APIRouter(prefix="/api/wallets", tags=["Wallets"])

def make_transaction_response(tx: Transaction, db: Session) -> TransactionResponse:
    stmt_wallet = select(Wallet).where(Wallet.id == tx.wallet_id)
    wallet = db.exec(stmt_wallet).first()
    owner_name = wallet.get_owner_name() if wallet else "Unknown"
    return TransactionResponse(
        id=tx.id,
        wallet_id=tx.wallet_id,
        transaction_type=tx.transaction_type,
        amount=tx.amount,
        status=tx.status,
        description=tx.description,
        wallet_owner=owner_name,
        created_at=tx.created_at,
        updated_at=tx.updated_at
    )

def make_wallet_response(wallet: Wallet) -> WalletResponse:
    owner_name = wallet.get_owner_name()
    owner_type = "Renter" if wallet.renter_id else "Host" if wallet.host_id else "Unknown"
    return WalletResponse(
        id=wallet.id,
        balance=wallet.balance,
        currency=wallet.currency,
        owner_name=owner_name,
        owner_type=owner_type,
        created_at=wallet.created_at,
        updated_at=wallet.updated_at
    )

@router.get("/", response_model=WalletDetailResponse)
def get_user_wallet(user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    stmt_renter = select(Renter).where(Renter.user_id == user.id)
    renter = db.exec(stmt_renter).first()
    if renter:
        wallet = renter.get_wallet(db)
    else:
        stmt_host = select(Host).where(Host.user_id == user.id)
        host = db.exec(stmt_host).first()
        if host:
            wallet = host.get_wallet(db)
        else:
            raise HTTPException(status_code=404, detail="No wallet profile found for user")
            
    stmt_txs = select(Transaction).where(Transaction.wallet_id == wallet.id).order_by(Transaction.created_at.desc())
    txs = db.exec(stmt_txs).all()
    owner_name = wallet.get_owner_name()
    
    return WalletDetailResponse(
        id=wallet.id,
        balance=wallet.balance,
        currency=wallet.currency,
        owner_name=owner_name,
        transactions=[make_transaction_response(tx, db) for tx in txs],
        created_at=wallet.created_at,
        updated_at=wallet.updated_at
    )

@router.post("/add_funds/")
def add_funds(payload: WalletUpdatePayload, user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    if payload.amount <= 0:
        raise HTTPException(status_code=400, detail="Valid amount is required")
        
    stmt_renter = select(Renter).where(Renter.user_id == user.id)
    renter = db.exec(stmt_renter).first()
    if not renter:
        raise HTTPException(status_code=403, detail="Only renters can add funds")
        
    try:
        new_balance = renter.add_money(db, payload.amount, payload.description)
        return {
            "message": "Funds added successfully",
            "new_balance": float(new_balance),
            "amount_added": payload.amount
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/withdraw_funds/")
def withdraw_funds(payload: WalletUpdatePayload, user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    if payload.amount <= 0:
        raise HTTPException(status_code=400, detail="Valid amount is required")
        
    stmt_host = select(Host).where(Host.user_id == user.id)
    host = db.exec(stmt_host).first()
    if not host:
        raise HTTPException(status_code=403, detail="Only hosts can withdraw funds")
        
    try:
        new_balance = host.withdraw_money(db, payload.amount, payload.description)
        return {
            "message": "Funds withdrawn successfully",
            "new_balance": float(new_balance),
            "amount_withdrawn": payload.amount
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
