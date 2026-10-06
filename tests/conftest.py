"""Shared pytest fixtures: an isolated test database and ready-to-use API clients."""

import os

# These must be set BEFORE anything from `app` is imported, because
# app/core/config.py reads the environment at import time. Environment
# variables win over the .env file, so the real database is never used.
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key-not-used-anywhere-else"
os.environ["ALGORITHM"] = "HS256"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.database.session import get_db
from app.main import app

API = "/api/v1"

# StaticPool = every session shares one connection, so they all see the same
# in-memory database.
test_engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(test_engine, "connect")
def enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    # SQLite ignores ON DELETE CASCADE / SET NULL unless this is switched on.
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestSessionLocal = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    """API client backed by a brand-new empty database for every test."""
    Base.metadata.create_all(bind=test_engine)
    app.dependency_overrides[get_db] = override_get_db
    # Not used as a context manager on purpose: that would run the startup
    # check against the real database.
    yield TestClient(app)
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


def register_and_login(client: TestClient, email: str) -> dict[str, str]:
    """Create a user and return the Authorization header for them."""
    password = "correct-horse-battery"
    response = client.post(
        f"{API}/auth/register",
        json={"email": email, "full_name": "Test User", "password": password},
    )
    assert response.status_code == 201, response.text

    response = client.post(
        f"{API}/auth/login", data={"username": email, "password": password}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def auth_headers(client):
    """Authorization header of the main test user."""
    return register_and_login(client, "owner@example.com")


@pytest.fixture
def other_user_headers(client):
    """Authorization header of a second user, for 'cannot touch my data' tests."""
    return register_and_login(client, "intruder@example.com")
