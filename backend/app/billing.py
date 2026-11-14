"""Wallet movements and ending sessions. Callers commit; nothing here commits, so each
request is one database transaction."""
import logging
import uuid
from decimal import Decimal
from typing import Optional

from sqlmodel import Session as DB, select

from app import cloudflare
from app.models import GPU, Host, Session, Transaction, Wallet, utcnow

log = logging.getLogger(__name__)


def wallet_of(db: DB, *, renter_id: Optional[uuid.UUID] = None, host_id: Optional[uuid.UUID] = None) -> Wallet:
    """The owner's wallet, row-locked (on PostgreSQL) until the transaction ends."""
    col = Wallet.renter_id if renter_id else Wallet.host_id
    wallet = db.exec(select(Wallet).where(col == (renter_id or host_id)).with_for_update()).first()
    if not wallet:  # created at sign-up; this only covers accounts made before that
        wallet = Wallet(renter_id=renter_id, host_id=host_id)
        db.add(wallet)
        db.flush()
    return wallet


def post(db: DB, wallet: Wallet, kind: str, amount: Decimal, description: str) -> Transaction:
    """Record a movement and apply it to the balance. Payments and withdrawals subtract."""
    wallet.balance += -amount if kind in ("RENTAL_PAYMENT", "WITHDRAWAL") else amount
    tx = Transaction(wallet_id=wallet.id, transaction_type=kind, amount=amount, description=description)
    db.add_all([wallet, tx])
    db.flush()
    return tx


def close_session(db: DB, s: Session, gpu_name: str) -> Decimal:
    """End an open session: charge the renter, pay the host, stop routing to its container."""
    s.end_time = utcnow()
    if s.status == "PENDING" or not s.start_time:
        s.status, s.total_cost = "CANCELLED", Decimal("0.00")
    else:
        s.total_cost = s.cost_so_far()
        s.status = "COMPLETED"
        if s.total_cost > 0:
            paid = post(db, wallet_of(db, renter_id=s.renter_id), "RENTAL_PAYMENT", s.total_cost, f"{gpu_name} session")
            post(db, wallet_of(db, host_id=s.host_id), "RENTAL_EARNING", s.total_cost, f"{gpu_name} session")
            s.payment_transaction_id = paid.id
    db.add(s)
    db.flush()
    if s.ssh_host:
        close_route(db, s)
    return s.total_cost


def host_routes(db: DB, host_id: uuid.UUID) -> dict[str, int]:
    """{hostname: container port} for every running session on this host."""
    rows = db.exec(select(Session.ssh_host, Session.host_port).where(
        Session.host_id == host_id, Session.status == "ACTIVE", Session.ssh_host.is_not(None),
    )).all()
    return {h: p for h, p in rows}


def close_route(db: DB, s: Session) -> None:
    """Stop routing an ended session's hostname. Billing never waits on Cloudflare."""
    host = db.get(Host, s.host_id)
    try:
        # Rewriting the routes is what cuts access; the DNS record is only cleanup.
        cloudflare.set_routes(host.tunnel_id, host_routes(db, s.host_id))
        if s.dns_record_id:
            cloudflare.remove_dns(s.dns_record_id)
            s.dns_record_id = None
    except cloudflare.CloudflareError:
        log.exception("Couldn't remove the Cloudflare route for session %s", s.id)


def end_overdue_sessions(db: DB, host_id: uuid.UUID) -> None:
    """End this host's running sessions whose cost has reached the renter's balance.

    Called whenever the host's agent polls (every few seconds), so a renter can't run
    far past what they can pay.
    """
    # ponytail: piggybacks on agent polling; if an agent goes offline its sessions keep
    # running until a participant ends them. A scheduled job would close that gap.
    running = db.exec(select(Session).where(Session.host_id == host_id, Session.status == "ACTIVE")).all()
    for s in running:
        balance = db.exec(select(Wallet.balance).where(Wallet.renter_id == s.renter_id)).first() or Decimal(0)
        if s.cost_so_far() >= balance:
            close_session(db, s, db.get(GPU, s.gpu_id).gpu_name)
            s.connection_error = "Ended because the renter's wallet ran out."

