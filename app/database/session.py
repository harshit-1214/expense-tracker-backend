"""
Database engine and session management.

    engine                     -> the connection pool to PostgreSQL
    SessionLocal               -> factory that creates database sessions
    get_db                     -> FastAPI dependency: one session per request
    check_database_connection  -> used at startup and by the health check
"""

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.database_url,
    # Test each pooled connection before using it, so a database restart
    # does not surface as random "server closed the connection" errors.
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    """Open a session for the request and always close it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_connection() -> None:
    """Run a trivial query; raises an exception if the database is unreachable."""
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
