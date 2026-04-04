from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from config import settings

_url = settings.database_url

# SQLite needs check_same_thread=False; PostgreSQL needs pool settings for serverless
if _url.startswith("sqlite"):
    engine = create_engine(_url, connect_args={"check_same_thread": False})
else:
    import re
    import ssl
    from sqlalchemy.pool import NullPool

    # Use pg8000 (pure Python driver) — required on Vercel where psycopg2 is unavailable
    _pg_url = re.sub(r"^postgresql(\+\w+)?://", "postgresql+pg8000://", _url)

    # Supabase connection pooler requires username format "postgres.PROJECT_REF".
    # Auto-fix if the host is a pooler host and the username is plain "postgres".
    _pooler_match = re.search(r"pooler\.supabase\.com", _pg_url)
    if _pooler_match:
        _project_ref_match = re.search(r"aarysgprbhdiggjtqoif", _pg_url)
        if not _project_ref_match:
            _pg_url = re.sub(
                r"(postgresql\+pg8000://)postgres:",
                r"\1postgres.aarysgprbhdiggjtqoif:",
                _pg_url,
            )

    # Supabase requires SSL — pg8000 needs it passed explicitly via connect_args
    _ssl_context = ssl.create_default_context()
    _ssl_context.check_hostname = False
    _ssl_context.verify_mode = ssl.CERT_NONE

    engine = create_engine(
        _pg_url,
        connect_args={"ssl_context": _ssl_context},
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
