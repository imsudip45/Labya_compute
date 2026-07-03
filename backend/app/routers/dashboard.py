from datetime import date
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from app.db import get_session
from app.models import User, Renter, Host, GPU, Session as Session_Model, Transaction
from app.schemas import DashboardStatsResponse
from app.auth_utils import get_current_user

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

@router.get("/stats/", response_model=DashboardStatsResponse)
def get_dashboard_stats(user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    stmt_host = select(Host).where(Host.user_id == user.id)
    host = db.exec(stmt_host).first()
    
    stmt_renter = select(Renter).where(Renter.user_id == user.id)
    renter = db.exec(stmt_renter).first()
    
    if host:
        stmt_gpus = select(GPU).where(GPU.host_id == host.id)
        gpus = db.exec(stmt_gpus).all()
        total_gpus = len(gpus)
        available_gpus = len([g for g in gpus if g.gpu_availability])
        
        stmt_sessions = select(Session_Model).where(Session_Model.host_id == host.id, Session_Model.status == "ACTIVE")
        active_sessions = len(db.exec(stmt_sessions).all())
        
        wallet = host.get_wallet(db)
        today = date.today()
        stmt_tx = select(Transaction).where(
            Transaction.wallet_id == wallet.id,
            Transaction.transaction_type == "RENTAL_EARNING"
        )
        txs = db.exec(stmt_tx).all()
        todays_earnings = sum(t.amount for t in txs if t.created_at.date() == today)
        
        return DashboardStatsResponse(
            totalGPUs=total_gpus,
            activeSessions=active_sessions,
            todaysEarnings=float(todays_earnings),
            availableGPUs=available_gpus
        )
        
    elif renter:
        stmt_sessions = select(Session_Model).where(Session_Model.renter_id == renter.id)
        sessions = db.exec(stmt_sessions).all()
        total_sessions = len(sessions)
        active_sessions = len([s for s in sessions if s.status == "ACTIVE"])
        
        wallet = renter.get_wallet(db)
        stmt_tx = select(Transaction).where(
            Transaction.wallet_id == wallet.id,
            Transaction.transaction_type == "RENTAL_PAYMENT"
        )
        txs = db.exec(stmt_tx).all()
        total_spent = sum(t.amount for t in txs)
        
        return DashboardStatsResponse(
            totalSessions=total_sessions,
            activeSessions=active_sessions,
            totalSpent=float(total_spent)
        )
        
    return DashboardStatsResponse()
