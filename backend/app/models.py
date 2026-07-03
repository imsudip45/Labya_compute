import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from sqlmodel import Field, Relationship, SQLModel, Session, select

class User(SQLModel, table=True):
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    first_name: str
    last_name: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    renter_profile: Optional["Renter"] = Relationship(back_populates="user", sa_relationship_kwargs={"uselist": False, "cascade": "all, delete-orphan"})
    host_profile: Optional["Host"] = Relationship(back_populates="user", sa_relationship_kwargs={"uselist": False, "cascade": "all, delete-orphan"})

class Renter(SQLModel, table=True):
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", unique=True)
    
    # Relationships
    user: User = Relationship(back_populates="renter_profile")
    wallet: Optional["Wallet"] = Relationship(back_populates="renter", sa_relationship_kwargs={"uselist": False, "cascade": "all, delete-orphan"})
    sessions: List["Session"] = Relationship(back_populates="renter")

    def get_wallet(self, db_session: Session) -> "Wallet":
        statement = select(Wallet).where(Wallet.renter_id == self.id)
        wallet = db_session.exec(statement).first()
        if not wallet:
            wallet = Wallet(renter_id=self.id, balance=Decimal("0.00"))
            db_session.add(wallet)
            db_session.commit()
            db_session.refresh(wallet)
        return wallet

    def add_money(self, db_session: Session, amount: float, description: str = "Deposit") -> Decimal:
        wallet = self.get_wallet(db_session)
        wallet.balance += Decimal(str(amount))
        db_session.add(wallet)
        
        transaction = Transaction(
            wallet_id=wallet.id,
            transaction_type="DEPOSIT",
            amount=Decimal(str(amount)),
            description=description,
            status="COMPLETED"
        )
        db_session.add(transaction)
        db_session.commit()
        db_session.refresh(wallet)
        return wallet.balance

    def pay_for_rental(self, db_session: Session, amount: float, description: str = "Rental payment") -> Decimal:
        wallet = self.get_wallet(db_session)
        if wallet.balance < Decimal(str(amount)):
            raise ValueError("Insufficient balance")
        wallet.balance -= Decimal(str(amount))
        db_session.add(wallet)
        
        transaction = Transaction(
            wallet_id=wallet.id,
            transaction_type="RENTAL_PAYMENT",
            amount=Decimal(str(amount)),
            description=description,
            status="COMPLETED"
        )
        db_session.add(transaction)
        db_session.commit()
        db_session.refresh(wallet)
        return wallet.balance

class Host(SQLModel, table=True):
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", unique=True)
    
    # Relationships
    user: User = Relationship(back_populates="host_profile")
    wallet: Optional["Wallet"] = Relationship(back_populates="host", sa_relationship_kwargs={"uselist": False, "cascade": "all, delete-orphan"})
    gpus: List["GPU"] = Relationship(back_populates="host")
    sessions: List["Session"] = Relationship(back_populates="host")

    def get_wallet(self, db_session: Session) -> "Wallet":
        statement = select(Wallet).where(Wallet.host_id == self.id)
        wallet = db_session.exec(statement).first()
        if not wallet:
            wallet = Wallet(host_id=self.id, balance=Decimal("0.00"))
            db_session.add(wallet)
            db_session.commit()
            db_session.refresh(wallet)
        return wallet

    def add_earning(self, db_session: Session, amount: float, description: str = "Rental earning") -> Decimal:
        wallet = self.get_wallet(db_session)
        wallet.balance += Decimal(str(amount))
        db_session.add(wallet)
        
        transaction = Transaction(
            wallet_id=wallet.id,
            transaction_type="RENTAL_EARNING",
            amount=Decimal(str(amount)),
            description=description,
            status="COMPLETED"
        )
        db_session.add(transaction)
        db_session.commit()
        db_session.refresh(wallet)
        return wallet.balance

    def withdraw_money(self, db_session: Session, amount: float, description: str = "Withdrawal") -> Decimal:
        wallet = self.get_wallet(db_session)
        if wallet.balance < Decimal(str(amount)):
            raise ValueError("Insufficient balance")
        wallet.balance -= Decimal(str(amount))
        db_session.add(wallet)
        
        transaction = Transaction(
            wallet_id=wallet.id,
            transaction_type="WITHDRAWAL",
            amount=Decimal(str(amount)),
            description=description,
            status="COMPLETED"
        )
        db_session.add(transaction)
        db_session.commit()
        db_session.refresh(wallet)
        return wallet.balance

class Wallet(SQLModel, table=True):
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    renter_id: Optional[uuid.UUID] = Field(foreign_key="renter.id", unique=True, nullable=True)
    host_id: Optional[uuid.UUID] = Field(foreign_key="host.id", unique=True, nullable=True)
    balance: Decimal = Field(default=Decimal("0.00"), max_digits=10, decimal_places=2)
    currency: str = "NPR"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    renter: Optional[Renter] = Relationship(back_populates="wallet")
    host: Optional[Host] = Relationship(back_populates="wallet")
    transactions: List["Transaction"] = Relationship(back_populates="wallet")

class Transaction(SQLModel, table=True):
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    wallet_id: uuid.UUID = Field(foreign_key="wallet.id")
    transaction_type: str  # DEPOSIT, WITHDRAWAL, RENTAL_PAYMENT, RENTAL_EARNING
    amount: Decimal = Field(max_digits=10, decimal_places=2)
    status: str = "COMPLETED"  # PENDING, COMPLETED, FAILED, CANCELLED
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    wallet: Wallet = Relationship(back_populates="transactions")

class GPU(SQLModel, table=True):
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    host_id: uuid.UUID = Field(foreign_key="host.id")
    gpu_name: str
    gpu_model: Optional[str] = None
    gpu_memory: int
    gpu_price: int
    gpu_availability: bool = True
    gpu_location: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    host: Host = Relationship(back_populates="gpus")
    sessions: List["Session"] = Relationship(back_populates="gpu")

class Session(SQLModel, table=True):
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    gpu_id: uuid.UUID = Field(foreign_key="gpu.id")
    renter_id: uuid.UUID = Field(foreign_key="renter.id")
    host_id: uuid.UUID = Field(foreign_key="host.id")
    
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: str = "PENDING"  # PENDING, ACTIVE, COMPLETED, CANCELLED, FAILED
    
    ssh_host: Optional[str] = None
    ssh_port: Optional[int] = 22
    ssh_username: Optional[str] = None
    ssh_password: Optional[str] = None
    
    connection_status: str = "CONNECTING"  # CONNECTING, CONNECTED, DISCONNECTED, ERROR
    connection_error: Optional[str] = None
    last_connected: Optional[datetime] = None
    
    gpu_utilization: int = 0
    memory_utilization: int = 0
    temperature: int = 0
    
    is_auto_reconnect: bool = True
    payment_transaction_id: Optional[uuid.UUID] = Field(foreign_key="transaction.id", nullable=True)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    gpu: GPU = Relationship(back_populates="sessions")
    renter: Renter = Relationship(back_populates="sessions")
    host: Host = Relationship(back_populates="sessions")
    relay_port: Optional["RelayPort"] = Relationship(back_populates="leased_to_session", sa_relationship_kwargs={"uselist": False})

    @property
    def total_cost(self) -> Decimal:
        if not self.start_time:
            return Decimal("0.00")
        end = self.end_time or datetime.utcnow()
        duration = end - self.start_time
        hours = duration.total_seconds() / 3600
        return Decimal(str(round(self.gpu.gpu_price * hours, 2)))

    def process_payment(self, db_session: Session) -> Decimal:
        total_cost = self.total_cost
        
        # Renter pays
        self.renter.pay_for_rental(
            db_session=db_session,
            amount=float(total_cost),
            description=f"Payment for {self.gpu.gpu_name} rental"
        )
        
        # Host receives
        self.host.add_earning(
            db_session=db_session,
            amount=float(total_cost),
            description=f"Earning from {self.gpu.gpu_name} rental"
        )
        
        self.status = "COMPLETED"
        db_session.add(self)
        db_session.commit()
        db_session.refresh(self)
        return total_cost

class RelayPort(SQLModel, table=True):
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    port: int = Field(unique=True)
    status: str = "FREE"  # FREE, LEASED, RESERVED
    leased_to_session_id: Optional[uuid.UUID] = Field(foreign_key="session.id", unique=True, nullable=True)
    leased_at: Optional[datetime] = None
    released_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    leased_to_session: Optional[Session] = Relationship(back_populates="relay_port")

    @classmethod
    def lease_free_port(cls, db_session: Session, session_obj: Session, start_port: int, end_port: int) -> "RelayPort":
        # Find FREE port using select_for_update for safety
        statement = select(cls).where(cls.status == "FREE", cls.port >= start_port, cls.port <= end_port).order_by(cls.port).with_for_update()
        free_port = db_session.exec(statement).first()
        
        if not free_port:
            # Look up used port values
            used_stmt = select(cls.port).where(cls.port >= start_port, cls.port <= end_port)
            used = set(db_session.exec(used_stmt).all())
            chosen = None
            for p in range(start_port, end_port + 1):
                if p not in used:
                    chosen = p
                    break
            if chosen is None:
                raise ValueError("No relay ports available in the configured range")
            free_port = cls(port=chosen, status="FREE")
            db_session.add(free_port)
            db_session.commit()
            db_session.refresh(free_port)
            
        free_port.status = "LEASED"
        free_port.leased_to_session_id = session_obj.id
        free_port.leased_at = datetime.utcnow()
        free_port.released_at = None
        db_session.add(free_port)
        db_session.commit()
        db_session.refresh(free_port)
        return free_port

    def release(self, db_session: Session):
        self.status = "FREE"
        self.released_at = datetime.utcnow()
        self.leased_to_session_id = None
        db_session.add(self)
        db_session.commit()
        db_session.refresh(self)
