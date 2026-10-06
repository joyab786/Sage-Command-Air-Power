"""Unit tests for Aero database connection and transaction handling."""

import os
import tempfile
import pytest
from sqlalchemy import text
from app.db.database import (
    create_aero_engine,
    init_db,
    close_db,
    get_db_session,
    check_database_health,
)
from app.core.config import Settings


def test_database_initialization_and_health():
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp:
        db_path = tmp.name

    try:
        settings = Settings(
            DATABASE_URL=f"sqlite:///{db_path}",
            DATABASE_WAL_MODE=True,
        )
        engine = init_db(settings=settings)
        assert engine is not None

        health = check_database_health()
        assert health["status"] == "HEALTHY"
        assert health["connected"] is True
        assert health["driver"] == "sqlite"
        assert health["wal_mode"] is True

    finally:
        close_db()
        if os.path.exists(db_path):
            os.remove(db_path)


def test_database_transaction_commit():
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp:
        db_path = tmp.name

    try:
        settings = Settings(DATABASE_URL=f"sqlite:///{db_path}")
        init_db(settings=settings)

        # 1. Execute DDL and insert within transactional session
        with get_db_session() as session:
            session.execute(text("CREATE TABLE test_data (id INTEGER PRIMARY KEY, name TEXT);"))
            session.execute(text("INSERT INTO test_data (name) VALUES ('entry_1');"))

        # 2. Verify commit persisted in fresh session
        with get_db_session() as session:
            result = session.execute(text("SELECT name FROM test_data WHERE id=1;")).scalar()
            assert result == "entry_1"

    finally:
        close_db()
        if os.path.exists(db_path):
            os.remove(db_path)


def test_database_transaction_rollback():
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp:
        db_path = tmp.name

    try:
        settings = Settings(DATABASE_URL=f"sqlite:///{db_path}")
        init_db(settings=settings)

        with get_db_session() as session:
            session.execute(text("CREATE TABLE rollback_test (id INTEGER PRIMARY KEY, val TEXT);"))

        # Trigger deliberate exception to test atomic rollback
        with pytest.raises(RuntimeError):
            with get_db_session() as session:
                session.execute(text("INSERT INTO rollback_test (val) VALUES ('uncommitted');"))
                raise RuntimeError("Simulated operational failure")

        # Verify record was rolled back
        with get_db_session() as session:
            count = session.execute(text("SELECT COUNT(*) FROM rollback_test;")).scalar()
            assert count == 0

    finally:
        close_db()
        if os.path.exists(db_path):
            os.remove(db_path)
