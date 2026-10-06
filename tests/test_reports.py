"""Tests for the spending reports."""

from decimal import Decimal

import pytest

from tests.conftest import API


@pytest.fixture
def sample_expenses(client, auth_headers):
    """Food: 100 + 300 (Jan), Rent: 500 (Feb), uncategorized: 100 (Feb) -> total 1000."""
    food = client.post(f"{API}/categories", json={"name": "Food"}, headers=auth_headers).json()
    rent = client.post(f"{API}/categories", json={"name": "Rent"}, headers=auth_headers).json()

    expenses = [
        {"title": "Snacks", "amount": "100.00", "expense_date": "2026-01-10", "category_id": food["id"]},
        {"title": "Dinner", "amount": "300.00", "expense_date": "2026-01-20", "category_id": food["id"]},
        {"title": "Room rent", "amount": "500.00", "expense_date": "2026-02-01", "category_id": rent["id"]},
        {"title": "Misc", "amount": "100.00", "expense_date": "2026-02-15"},
    ]
    for expense in expenses:
        response = client.post(f"{API}/expenses", json=expense, headers=auth_headers)
        assert response.status_code == 201, response.text

    return {"food_id": food["id"], "rent_id": rent["id"]}


def test_summary(client, auth_headers, sample_expenses):
    summary = client.get(f"{API}/reports/summary", headers=auth_headers).json()

    assert Decimal(summary["total_amount"]) == Decimal("1000.00")
    assert summary["expense_count"] == 4
    assert Decimal(summary["average_amount"]) == Decimal("250.00")
    assert Decimal(summary["highest_amount"]) == Decimal("500.00")


def test_summary_respects_date_range(client, auth_headers, sample_expenses):
    summary = client.get(
        f"{API}/reports/summary",
        params={"start_date": "2026-01-01", "end_date": "2026-01-31"},
        headers=auth_headers,
    ).json()

    assert Decimal(summary["total_amount"]) == Decimal("400.00")
    assert summary["expense_count"] == 2


def test_summary_with_no_expenses_is_all_zero(client, auth_headers):
    summary = client.get(f"{API}/reports/summary", headers=auth_headers).json()

    assert Decimal(summary["total_amount"]) == Decimal("0.00")
    assert summary["expense_count"] == 0
    assert Decimal(summary["average_amount"]) == Decimal("0.00")
    assert Decimal(summary["highest_amount"]) == Decimal("0.00")


def test_spending_by_category(client, auth_headers, sample_expenses):
    rows = client.get(f"{API}/reports/by-category", headers=auth_headers).json()

    # Biggest category first.
    assert rows[0]["category_name"] == "Rent"
    assert rows[0]["category_id"] == sample_expenses["rent_id"]
    assert Decimal(rows[0]["total_amount"]) == Decimal("500.00")
    assert rows[0]["percentage_of_total"] == 50.0

    by_name = {row["category_name"]: row for row in rows}
    assert Decimal(by_name["Food"]["total_amount"]) == Decimal("400.00")
    assert by_name["Food"]["expense_count"] == 2
    assert by_name["Food"]["percentage_of_total"] == 40.0
    assert by_name["Uncategorized"]["category_id"] is None
    assert Decimal(by_name["Uncategorized"]["total_amount"]) == Decimal("100.00")


def test_spending_by_category_with_no_expenses_is_empty(client, auth_headers):
    assert client.get(f"{API}/reports/by-category", headers=auth_headers).json() == []


def test_monthly_spending_returns_all_twelve_months(client, auth_headers, sample_expenses):
    months = client.get(
        f"{API}/reports/monthly", params={"year": 2026}, headers=auth_headers
    ).json()

    assert [row["month"] for row in months] == list(range(1, 13))
    assert Decimal(months[0]["total_amount"]) == Decimal("400.00")  # January
    assert months[0]["expense_count"] == 2
    assert Decimal(months[1]["total_amount"]) == Decimal("600.00")  # February
    assert Decimal(months[2]["total_amount"]) == Decimal("0.00")  # March: nothing spent
    assert months[2]["expense_count"] == 0


def test_reports_only_include_my_own_expenses(client, auth_headers, other_user_headers, sample_expenses):
    summary = client.get(f"{API}/reports/summary", headers=other_user_headers).json()

    assert summary["expense_count"] == 0
    assert Decimal(summary["total_amount"]) == Decimal("0.00")
