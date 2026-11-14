from sqlmodel import Session, create_engine

from app.config import settings

_sqlite = settings.sqlalchemy_url.startswith("sqlite")
engine = create_engine(
    settings.sqlalchemy_url,
    pool_pre_ping=True,
    # prepare_threshold=None: poolers in transaction mode (Supabase, Neon) can't keep
    # server-side prepared statements between transactions.
    connect_args={"check_same_thread": False} if _sqlite else {"prepare_threshold": None},
    **({} if _sqlite else {"pool_size": 5, "max_overflow": 10, "pool_recycle": 300}),
)


def get_session():
    with Session(engine) as session:
        yield session
