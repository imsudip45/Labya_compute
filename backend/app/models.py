"""Database tables. Schema changes need an Alembic migration (see README)."""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import CheckConstraint
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    """All stored times are timezone-aware UTC."""
    return datetime.now(timezone.utc)


def _updated():
    return Field(default_factory=utcnow, sa_column_kwargs={"onupdate": utcnow})


class User(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(unique=True, index=True, max_length=254)  # stored lowercase
    hashed_password: str = Field(max_length=100)
    first_name: str = Field(max_length=100)
    last_name: str = Field(default="", max_length=100)
    # Bumped on logout to revoke every token issued before it.
    token_version: int = 0
    failed_logins: int = 0
    locked_until: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utcnow)

    @property
    def display_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip() or self.email


class Renter(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", unique=True)


class Host(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", unique=True)
    # The Cloudflare tunnel this host's agent runs, created the first time the agent asks.
    tunnel_id: Optional[str] = Field(default=None, max_length=64)


class Wallet(SQLModel, table=True):
    __table_args__ = (
        CheckConstraint("(renter_id IS NULL) <> (host_id IS NULL)", name="wallet_one_owner"),
    )
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    renter_id: Optional[uuid.UUID] = Field(default=None, foreign_key="renter.id", unique=True)
    host_id: Optional[uuid.UUID] = Field(default=None, foreign_key="host.id", unique=True)
    # Can go below zero if a session runs past the renter's balance; new rentals are then blocked.
    balance: Decimal = Field(default=Decimal("0.00"), max_digits=12, decimal_places=2)
    currency: str = Field(default="NPR", max_length=3)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = _updated()


class Transaction(SQLModel, table=True):
    __table_args__ = (CheckConstraint("amount >= 0", name="transaction_amount_not_negative"),)
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    wallet_id: uuid.UUID = Field(foreign_key="wallet.id", index=True)
    transaction_type: str = Field(max_length=20)  # DEPOSIT, WITHDRAWAL, RENTAL_PAYMENT, RENTAL_EARNING
    amount: Decimal = Field(max_digits=12, decimal_places=2)
    status: str = Field(default="COMPLETED", max_length=20)
    description: Optional[str] = Field(default=None, max_length=200)
    created_at: datetime = Field(default_factory=utcnow, index=True)
    updated_at: datetime = _updated()


class GPU(SQLModel, table=True):
    __table_args__ = (
        CheckConstraint("gpu_price > 0", name="gpu_price_positive"),
        CheckConstraint("gpu_memory > 0", name="gpu_memory_positive"),
    )
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    host_id: uuid.UUID = Field(foreign_key="host.id", index=True)
    gpu_name: str = Field(max_length=100)
    gpu_model: Optional[str] = Field(default=None, max_length=100)
    gpu_memory: int  # GB
    gpu_price: int  # NPR per hour
    # The host's choice to list it. Whether it is rented right now comes from its sessions.
    gpu_availability: bool = True
    gpu_location: str = Field(max_length=100)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = _updated()


OPEN_STATUSES = ("PENDING", "ACTIVE")


class Session(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    gpu_id: uuid.UUID = Field(foreign_key="gpu.id", index=True)
    renter_id: uuid.UUID = Field(foreign_key="renter.id", index=True)
    host_id: uuid.UUID = Field(foreign_key="host.id", index=True)
    # Price per hour at the time of renting, so later price edits don't change the bill.
    hourly_price: int

    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: str = Field(default="PENDING", max_length=20, index=True)  # PENDING, ACTIVE, COMPLETED, CANCELLED

    ssh_host: Optional[str] = Field(default=None, max_length=255)  # sess-<id>.<tunnel_domain>, set when started
    ssh_username: Optional[str] = Field(default=None, max_length=64)
    ssh_password: Optional[str] = Field(default=None, max_length=128)
    host_port: Optional[int] = None  # the container's SSH port on the host's PC
    dns_record_id: Optional[str] = Field(default=None, max_length=64)

    connection_status: str = Field(default="CONNECTING", max_length=20)  # CONNECTING, CONNECTED, DISCONNECTED, ERROR
    connection_error: Optional[str] = Field(default=None, max_length=500)
    last_connected: Optional[datetime] = None

    gpu_utilization: int = 0
    memory_utilization: int = 0
    temperature: int = 0

    total_cost: Decimal = Field(default=Decimal("0.00"), max_digits=12, decimal_places=2)  # set when it ends
    payment_transaction_id: Optional[uuid.UUID] = Field(default=None, foreign_key="transaction.id")

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = _updated()

    @property
    def hours(self) -> float:
        if not self.start_time:
            return 0.0
        return max(0.0, ((self.end_time or utcnow()) - self.start_time).total_seconds() / 3600)

    def cost_so_far(self) -> Decimal:
        if self.status not in OPEN_STATUSES:
            return self.total_cost
        return (Decimal(self.hourly_price) * Decimal(str(self.hours))).quantize(Decimal("0.01"))

    @property
    def ssh_connection_string(self) -> Optional[str]:
        # Cloudflare carries SSH over HTTPS, so the renter's ssh goes through cloudflared.
        if self.ssh_host and self.ssh_username and self.status == "ACTIVE":
            return f'ssh -o ProxyCommand="cloudflared access ssh --hostname %h" {self.ssh_username}@{self.ssh_host}'
        return None

