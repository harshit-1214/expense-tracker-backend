"""Tests for registration, login and token-protected endpoints."""

from tests.conftest import API

NEW_USER = {
    "email": "Asha@Example.com",
    "full_name": "Asha Verma",
    "password": "a-strong-password",
}


def test_register_returns_user_without_password(client):
    response = client.post(f"{API}/auth/register", json=NEW_USER)

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "asha@example.com"  # stored lowercase
    assert body["full_name"] == "Asha Verma"
    assert "password" not in body
    assert "hashed_password" not in body


def test_register_rejects_duplicate_email(client):
    client.post(f"{API}/auth/register", json=NEW_USER)

    # Same email with different capitalisation is still the same account.
    response = client.post(
        f"{API}/auth/register", json={**NEW_USER, "email": "asha@example.com"}
    )

    assert response.status_code == 409


def test_register_rejects_short_password(client):
    response = client.post(f"{API}/auth/register", json={**NEW_USER, "password": "short"})

    assert response.status_code == 422


def test_login_returns_working_token(client):
    client.post(f"{API}/auth/register", json=NEW_USER)

    response = client.post(
        f"{API}/auth/login",
        data={"username": NEW_USER["email"], "password": NEW_USER["password"]},
    )

    assert response.status_code == 200
    token = response.json()
    assert token["token_type"] == "bearer"

    profile = client.get(
        f"{API}/users/me", headers={"Authorization": f"Bearer {token['access_token']}"}
    )
    assert profile.status_code == 200
    assert profile.json()["email"] == "asha@example.com"


def test_login_rejects_wrong_password(client):
    client.post(f"{API}/auth/register", json=NEW_USER)

    response = client.post(
        f"{API}/auth/login",
        data={"username": NEW_USER["email"], "password": "wrong-password"},
    )

    assert response.status_code == 401


def test_login_rejects_unknown_email(client):
    response = client.post(
        f"{API}/auth/login",
        data={"username": "nobody@example.com", "password": "whatever-password"},
    )

    assert response.status_code == 401


def test_protected_endpoint_requires_token(client):
    assert client.get(f"{API}/users/me").status_code == 401
    assert client.get(f"{API}/expenses").status_code == 401


def test_protected_endpoint_rejects_invalid_token(client):
    response = client.get(
        f"{API}/users/me", headers={"Authorization": "Bearer not-a-real-token"}
    )

    assert response.status_code == 401
