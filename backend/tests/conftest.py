"""
SageCommand Air Power System (Aero) — Shared Test Fixtures.
Provides isolated in-memory databases, test settings, and FastAPI test clients.
"""

import sys
import os
import pytest
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker, Session

# Ensure backend root is on sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.config import Settings
from app.db.database import Base, get_db
import app.db.models  # Ensure all models are registered on Base.metadata
from app.main import create_app


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Returns deterministic test settings with in-memory database."""
    return Settings(
        APP_NAME="Aero Test Suite",
        ENV="testing",
        DEBUG=True,
        DATABASE_URL="sqlite:///:memory:",
        DATABASE_WAL_MODE=False,  # In-memory SQLite does not require WAL file
        DATABASE_ECHO=False,
        LOG_LEVEL="DEBUG",
        LOG_FORMAT="console",
    )


@pytest.fixture
def db_session(test_settings: Settings) -> Generator[Session, None, None]:
    """Provides isolated test database session per test using StaticPool."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = session_factory()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def test_client(test_settings: Settings, db_session: Session) -> Generator[TestClient, None, None]:
    """Provides TestClient with managed lifespan execution and isolated db session."""
    app = create_app(settings=test_settings)
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
