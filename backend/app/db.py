from sqlmodel import SQLModel, create_engine, Session
from app.config import settings

engine = create_engine(settings.get_database_url, echo=False)

def init_db():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
