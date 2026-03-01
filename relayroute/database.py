"""
SQLAlchemy sync engine and session factory (psycopg2).
"""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from relayroute.config import get_settings
from relayroute.models import Base

settings = get_settings()
engine = create_engine(
    settings.sync_database_url,
    echo=False,
    future=True,
)

session_factory = sessionmaker(
    engine,
    class_=Session,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


def get_db() -> Generator[Session, None, None]:
    """Dependency that yields a sync session. Use with FastAPI Depends()."""
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """Create all tables. Prefer Alembic migrations in production."""
    Base.metadata.create_all(bind=engine)
