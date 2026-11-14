from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.auth_utils import get_current_host, get_current_renter, get_current_user
from app.billing import post, wallet_of
from app.config import settings
from app.db import get_session
from app.models import Host, Renter, Transaction, User, Wallet
from app.schemas import BalanceResponse, TransactionResponse, WalletResponse, WalletUpdatePayload

router = APIRouter(prefix="/api/wallets", tags=["Wallets"])


@router.get("/", response_model=WalletResponse)
def my_wallet(user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    renter = db.exec(select(Renter).where(Renter.user_id == user.id)).first()
    host = None if renter else db.exec(select(Host).where(Host.user_id == user.id)).first()
    if not renter and not host:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This account has no wallet.")
    col = Wallet.renter_id if renter else Wallet.host_id
    wallet = db.exec(select(Wallet).where(col == (renter or host).id)).first()
    if not wallet:
        wallet = wallet_of(db, renter_id=renter.id) if renter else wallet_of(db, host_id=host.id)
        db.commit()
    txs = db.exec(
        select(Transaction).where(Transaction.wallet_id == wallet.id).order_by(Transaction.created_at.desc()).limit(500)
    ).all()
    return WalletResponse(
        id=wallet.id, balance=wallet.balance, currency=wallet.currency,
        owner_name=f"{'Renter' if renter else 'Host'}: {user.display_name}",
        transactions=[TransactionResponse(**t.model_dump()) for t in txs],
    )


@router.post("/add_funds/", response_model=BalanceResponse)
def add_funds(payload: WalletUpdatePayload, renter: Renter = Depends(get_current_renter), db: Session = Depends(get_session)):
    if not settings.simulated_payments:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Adding funds isn't available yet.")
    wallet = wallet_of(db, renter_id=renter.id)
    post(db, wallet, "DEPOSIT", payload.amount, payload.description or "Deposit")
    db.commit()
    return BalanceResponse(balance=wallet.balance)


@router.post("/withdraw_funds/", response_model=BalanceResponse)
def withdraw_funds(payload: WalletUpdatePayload, host: Host = Depends(get_current_host), db: Session = Depends(get_session)):
    if not settings.simulated_payments:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Withdrawals aren't available yet.")
    wallet = wallet_of(db, host_id=host.id)
    if wallet.balance < payload.amount:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You can't withdraw more than your balance.")
    post(db, wallet, "WITHDRAWAL", payload.amount, payload.description or "Withdrawal")
    db.commit()
    return BalanceResponse(balance=wallet.balance)
