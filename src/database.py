from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.config import settings
from src.models import Base

engine = None
SessionLocal = None

def get_engine():
    global engine
    if engine is None:
        engine = create_engine(settings.database_url, echo=False, pool_pre_ping=True)
    return engine

def get_session_local():
    global SessionLocal
    if SessionLocal is None:
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return SessionLocal

def get_db():
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    print("Database initialized")