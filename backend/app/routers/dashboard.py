from datetime import datetime, time

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlmodel import Session, select

from app.auth_utils import get_current_user
from app.db import get_session
from app.models import GPU, Host, Renter, Session as RentalSession, Transaction, User, Wallet, utcnow
from app.schemas import DashboardStatsResponse

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


def _sum(db: Session, wallet_col, owner_id, kind: str, since: datetime | None = None) -> float:
    q = (
        select(func.coalesce(func.sum(Transaction.amount), 0))
        .join(Wallet, Wallet.id == Transaction.wallet_id)
        .where(wallet_col == owner_id, Transaction.transaction_type == kind)
    )
    if since:
        q = q.where(Transaction.created_at >= since)
    return float(db.exec(q).one())


def _count(db: Session, model, *where) -> int:
    return db.exec(select(func.count()).select_from(model).where(*where)).one()


@router.get("/stats/", response_model=DashboardStatsResponse)
def stats(user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    host = db.exec(select(Host).where(Host.user_id == user.id)).first()
    if host:
        # "Today" is the UTC day, matching how timestamps are stored.
        midnight = datetime.combine(utcnow().date(), time.min)
        return DashboardStatsResponse(
            totalGPUs=_count(db, GPU, GPU.host_id == host.id),
            availableGPUs=_count(db, GPU, GPU.host_id == host.id, GPU.gpu_availability == True),  # noqa: E712
            activeSessions=_count(db, RentalSession, RentalSession.host_id == host.id, RentalSession.status == "ACTIVE"),
            todaysEarnings=_sum(db, Wallet.host_id, host.id, "RENTAL_EARNING", midnight),
        )
    renter = db.exec(select(Renter).where(Renter.user_id == user.id)).first()
    if renter:
        return DashboardStatsResponse(
            totalSessions=_count(db, RentalSession, RentalSession.renter_id == renter.id),
            activeSessions=_count(db, RentalSession, RentalSession.renter_id == renter.id, RentalSession.status == "ACTIVE"),
            totalSpent=_sum(db, Wallet.renter_id, renter.id, "RENTAL_PAYMENT"),
        )
    return DashboardStatsResponse()
