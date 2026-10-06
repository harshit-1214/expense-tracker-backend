"""Tests for expense CRUD, filters, pagination and ownership rules."""

from datetime import date
from decimal import Decimal

from tests.conftest import API


def create_expense(client, headers, **overrides):
    payload = {
        "title": "Groceries",
        "amount": "250.50",
        "expense_date": "2026-03-10",
        "payment_method": "upi",
        **overrides,
    }
    response = client.post(f"{API}/expenses", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def test_create_expense(client, auth_headers):
    category = client.post(
        f"{API}/categories", json={"name": "Food"}, headers=auth_headers
    ).json()

    expense = create_expense(
        client, auth_headers, category_id=category["id"], notes="Weekly shop"
    )

    assert expense["title"] == "Groceries"
    assert Decimal(expense["amount"]) == Decimal("250.50")
    assert expense["expense_date"] == "2026-03-10"
    assert expense["payment_method"] == "upi"
    assert expense["notes"] == "Weekly shop"
    assert expense["category"] == {"id": category["id"], "name": "Food"}


def test_create_expense_uses_defaults(client, auth_headers):
    response = client.post(
        f"{API}/expenses", json={"title": "Tea", "amount": "15"}, headers=auth_headers
    )

    assert response.status_code == 201
    expense = response.json()
    assert expense["expense_date"] == date.today().isoformat()
    assert expense["payment_method"] == "cash"
    assert expense["category"] is None


def test_create_expense_rejects_invalid_data(client, auth_headers):
    def post(**overrides):
        payload = {"title": "Bad", "amount": "10.00", **overrides}
        return client.post(f"{API}/expenses", json=payload, headers=auth_headers)

    assert post(amount="0").status_code == 422  # must be positive
    assert post(amount="-5").status_code == 422
    assert post(amount="10.999").status_code == 422  # max 2 decimal places
    assert post(title="   ").status_code == 422  # blank after trimming
    assert post(payment_method="bitcoin").status_code == 422
    assert post(category_id=9999).status_code == 404  # category does not exist


def test_cannot_use_another_users_category(client, auth_headers, other_user_headers):
    their_category = client.post(
        f"{API}/categories", json={"name": "Private"}, headers=other_user_headers
    ).json()

    response = client.post(
        f"{API}/expenses",
        json={"title": "Sneaky", "amount": "10", "category_id": their_category["id"]},
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_update_expense_changes_only_sent_fields(client, auth_headers):
    expense = create_expense(client, auth_headers, notes="Original note")

    response = client.patch(
        f"{API}/expenses/{expense['id']}",
        json={"amount": "300.00"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    updated = response.json()
    assert Decimal(updated["amount"]) == Decimal("300.00")
    assert updated["title"] == "Groceries"
    assert updated["notes"] == "Original note"


def test_update_expense_rejects_null_for_required_field(client, auth_headers):
    expense = create_expense(client, auth_headers)

    response = client.patch(
        f"{API}/expenses/{expense['id']}", json={"title": None}, headers=auth_headers
    )

    assert response.status_code == 422


def test_update_expense_can_remove_category(client, auth_headers):
    category = client.post(
        f"{API}/categories", json={"name": "Food"}, headers=auth_headers
    ).json()
    expense = create_expense(client, auth_headers, category_id=category["id"])

    response = client.patch(
        f"{API}/expenses/{expense['id']}",
        json={"category_id": None},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["category"] is None


def test_delete_expense(client, auth_headers):
    expense = create_expense(client, auth_headers)
    url = f"{API}/expenses/{expense['id']}"

    assert client.delete(url, headers=auth_headers).status_code == 204
    assert client.get(url, headers=auth_headers).status_code == 404


def test_other_user_cannot_see_or_change_my_expense(client, auth_headers, other_user_headers):
    expense = create_expense(client, auth_headers)
    url = f"{API}/expenses/{expense['id']}"

    assert client.get(url, headers=other_user_headers).status_code == 404
    assert client.patch(url, json={"amount": "1"}, headers=other_user_headers).status_code == 404
    assert client.delete(url, headers=other_user_headers).status_code == 404
    assert client.get(f"{API}/expenses", headers=other_user_headers).json()["total"] == 0

    # Still there for the real owner.
    assert client.get(url, headers=auth_headers).status_code == 200


def test_list_expenses_is_newest_first_and_paginated(client, auth_headers):
    create_expense(client, auth_headers, title="January", expense_date="2026-01-05")
    create_expense(client, auth_headers, title="March", expense_date="2026-03-05")
    create_expense(client, auth_headers, title="February", expense_date="2026-02-05")

    first_page = client.get(
        f"{API}/expenses", params={"limit": 2, "offset": 0}, headers=auth_headers
    ).json()
    second_page = client.get(
        f"{API}/expenses", params={"limit": 2, "offset": 2}, headers=auth_headers
    ).json()

    assert first_page["total"] == 3
    assert [expense["title"] for expense in first_page["items"]] == ["March", "February"]
    assert [expense["title"] for expense in second_page["items"]] == ["January"]


def test_list_expenses_filters(client, auth_headers):
    food = client.post(
        f"{API}/categories", json={"name": "Food"}, headers=auth_headers
    ).json()
    create_expense(
        client, auth_headers, title="Pizza night", amount="600",
        expense_date="2026-01-15", payment_method="card", category_id=food["id"],
    )
    create_expense(
        client, auth_headers, title="Bus pass", amount="1200",
        expense_date="2026-02-01", payment_method="upi",
    )
    create_expense(
        client, auth_headers, title="100% juice", amount="90",
        expense_date="2026-02-20", payment_method="cash", category_id=food["id"],
    )

    def titles(**params):
        response = client.get(f"{API}/expenses", params=params, headers=auth_headers)
        assert response.status_code == 200, response.text
        return sorted(expense["title"] for expense in response.json()["items"])

    assert titles(category_id=food["id"]) == ["100% juice", "Pizza night"]
    assert titles(payment_method="upi") == ["Bus pass"]
    assert titles(start_date="2026-02-01") == ["100% juice", "Bus pass"]
    assert titles(start_date="2026-01-01", end_date="2026-01-31") == ["Pizza night"]
    assert titles(min_amount="500") == ["Bus pass", "Pizza night"]
    assert titles(min_amount="100", max_amount="700") == ["Pizza night"]
    assert titles(search="PIZZA") == ["Pizza night"]  # case-insensitive
    assert titles(search="%") == ["100% juice"]  # % is a normal character


def test_list_expenses_rejects_reversed_date_range(client, auth_headers):
    response = client.get(
        f"{API}/expenses",
        params={"start_date": "2026-02-01", "end_date": "2026-01-01"},
        headers=auth_headers,
    )

    assert response.status_code == 422
