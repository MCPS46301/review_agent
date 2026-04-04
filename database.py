from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from config import settings

_url = settings.database_url

# SQLite needs check_same_thread=False; PostgreSQL needs pool settings for serverless
if _url.startswith("sqlite"):
    engine = create_engine(_url, connect_args={"check_same_thread": False})
else:
    # Use pg8000 (pure Python) driver — works on Vercel serverless without native libs
    # Convert postgresql:// → postgresql+pg8000://
    _pg_url = _url.replace("postgresql://", "postgresql+pg8000://", 1)
    from sqlalchemy.pool import NullPool
    engine = create_engine(
        _pg_url,
        poolclass=NullPool,
        pool_pre_ping=True,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from models import Review, ReviewResponse, Notification  # noqa: F401
    Base.metadata.create_all(bind=engine)
