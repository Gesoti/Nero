"""
Shared pytest fixtures for the WaterLevels test suite.

Design decisions:

- `in_memory_db` patches `app.db._get_connection` to always return the SAME
  in-memory sqlite3.Connection. This is necessary because SQLite ':memory:'
  databases are connection-local: each new connection gets a fresh empty DB,
  so the schema created by init_database() would be invisible to subsequent
  _get_connection() calls. By returning one shared connection we get a fully
  initialised schema that persists for the lifetime of a single test function.

  The shared connection's .close() method is neutralised so that production
  code that calls conn.close() after each query does not invalidate it.

- `async_client` uses ASGITransport (not starlette.testclient.TestClient) to
  avoid conflicting with the async lifespan. The app lifespan is NOT triggered,
  so APScheduler and upstream network calls never run in tests.
"""
from __future__ import annotations

import sqlite3
from unittest.mock import patch

import httpx
import pytest
import pytest_asyncio

from app.config import settings
from app.db import init_database
from app.main import app


class _SharedConnection:
    """
    Thin wrapper around a real sqlite3.Connection that delegates everything
    except close() — close() is a no-op so production code that closes after
    each query cannot invalidate the shared in-memory database.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def close(self) -> None:
        # Intentionally silenced: the shared connection must outlive each call.
        pass

    def __getattr__(self, name: str):
        return getattr(self._conn, name)

    # Context manager support (used by 'with conn:' in upsert functions)
    def __enter__(self):
        return self._conn.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self._conn.__exit__(exc_type, exc_val, exc_tb)


@pytest.fixture
def in_memory_db():
    """
    Provide a single shared in-memory SQLite connection for one test function.

    Steps:
    1. Open a real ':memory:' connection and keep it alive for the test.
    2. Patch `app.db._get_connection` so every call returns the same connection
       (wrapped to neutralise .close() calls).
    3. Call init_database() so all tables and indexes exist.
    4. Yield (test runs here).
    5. Tear down: the real underlying connection is closed after the test.
    """
    # The real underlying connection — never closed until teardown.
    real_conn = sqlite3.connect(":memory:", check_same_thread=False)
    real_conn.row_factory = sqlite3.Row
    real_conn.execute("PRAGMA journal_mode=WAL")
    real_conn.execute("PRAGMA foreign_keys=ON")

    shared = _SharedConnection(real_conn)

    with patch("app.db._get_connection", return_value=shared):
        # Also patch db_path to ':memory:' so init_database()'s Path().mkdir()
        # call resolves to Path('.').mkdir() which is a harmless no-op.
        with patch.object(settings, "db_path", ":memory:"):
            init_database()
            yield

    # Teardown: close the real underlying connection after the test finishes.
    real_conn.close()


@pytest_asyncio.fixture
async def async_client(in_memory_db):
    """
    httpx.AsyncClient wired to the FastAPI ASGI app via ASGITransport.
    The lifespan is not triggered (no APScheduler, no upstream network calls).
    """
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
