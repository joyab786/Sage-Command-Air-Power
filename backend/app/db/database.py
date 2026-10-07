"""
SageCommand Air Power System (Aero) — Database Foundation.
Provides SQLAlchemy 2.0 connection pooling, session lifecycle management,
transactional context managers, and SQLite Write-Ahead Logging (WAL) optimizations.
"""

from contextlib import contextmanager
from typing import Generator, Optional
from sqlalchemy import create_engine, event, text, Engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.core.exceptions import DatabaseError

logger = get_logger(__name__)

# Canonical SQLAlchemy Declarative Base
Base = declarative_base()

# Global engine and sessionmaker singletons
_engine: Optional[Engine] = None
_session_factory: Optional[sessionmaker] = None


def _configure_sqlite_pragmas(dbapi_connection, connection_record):
    """Configures high-concurrency PRAGMA settings for SQLite connections."""
    cursor = dbapi_connection.cursor()
    try:
        # WAL mode permits concurrent readers without blocking writers
        cursor.execute("PRAGMA journal_mode=WAL;")
        # NORMAL synchronous delivers safety under WAL mode with high write performance
        cursor.execute("PRAGMA synchronous=NORMAL;")
        # Set busy timeout to gracefully wait under concurrent bursts
        cursor.execute("PRAGMA busy_timeout=5000;")
        # Enforce referential integrity
        cursor.execute("PRAGMA foreign_keys=ON;")
    finally:
        cursor.close()


def create_aero_engine(settings: Optional[Settings] = None, database_url: Optional[str] = None) -> Engine:
    """Builds and configures SQLAlchemy engine with appropriate dialect tuning."""
    resolved_settings = settings or get_settings()
    url = database_url or resolved_settings.DATABASE_URL

    connect_args = {}
    if url.startswith("sqlite"):
        # check_same_thread=False allows multi-threaded async workers to access connections
        connect_args["check_same_thread"] = False
        connect_args["timeout"] = resolved_settings.DATABASE_BUSY_TIMEOUT_MS / 1000.0

    engine = create_engine(
        url,
        echo=resolved_settings.DATABASE_ECHO,
        connect_args=connect_args,
        future=True,
    )

    # Attach SQLite PRAGMA listener if using SQLite and WAL is requested
    if url.startswith("sqlite") and resolved_settings.DATABASE_WAL_MODE:
        event.listen(engine, "connect", _configure_sqlite_pragmas)

    return engine


def init_db(database_url: Optional[str] = None, settings: Optional[Settings] = None) -> Engine:
    """Initializes global database engine, registers schemas, and establishes sessionmaker."""
    global _engine, _session_factory

    resolved_settings = settings or get_settings()
    _engine = create_aero_engine(settings=resolved_settings, database_url=database_url)
    _session_factory = sessionmaker(
        bind=_engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )

    # Create registered tables
    try:
        import app.db.models  # noqa: F401
        Base.metadata.create_all(bind=_engine)
        logger.info(
            "Database foundation initialized successfully",
            extra={"url": database_url or resolved_settings.DATABASE_URL},
        )
    except Exception as exc:
        logger.error(f"Database initialization failed: {exc}", exc_info=True)
        raise DatabaseError(f"Failed to initialize database tables: {exc}") from exc

    return _engine


def get_engine() -> Engine:
    """Returns initialized engine singleton or initializes default."""
    global _engine
    if _engine is None:
        init_db()
    return _engine


def get_session_factory() -> sessionmaker:
    """Returns initialized session factory singleton."""
    global _session_factory
    if _session_factory is None:
        init_db()
    return _session_factory


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for atomic database transactions.
    Automatically commits on normal exit and rolls back on exception.
    """
    factory = get_session_factory()
    session: Session = factory()
    try:
        yield session
        session.commit()
    except Exception as exc:
        session.rollback()
        logger.error(f"Database transaction rollback triggered: {exc}")
        raise
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for injecting managed database sessions."""
    factory = get_session_factory()
    session: Session = factory()
    try:
        yield session
    finally:
        session.close()


def check_database_health() -> dict:
    """Verifies database connectivity and returns health diagnostics."""
    engine = get_engine()
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
            wal_enabled = False
            if engine.url.drivername.startswith("sqlite"):
                mode = conn.execute(text("PRAGMA journal_mode;")).scalar()
                wal_enabled = str(mode).upper() == "WAL"

            return {
                "status": "HEALTHY" if result == 1 else "DEGRADED",
                "connected": True,
                "driver": engine.url.drivername,
                "wal_mode": wal_enabled,
            }
    except Exception as exc:
        logger.error(f"Database health check failed: {exc}")
        return {
            "status": "UNHEALTHY",
            "connected": False,
            "error": str(exc),
        }


def close_db() -> None:
    """Disposes engine connection pool cleanly upon application shutdown."""
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("Database connection pool disposed")
