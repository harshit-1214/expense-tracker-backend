"""Tests for category CRUD and ownership rules."""

from tests.conftest import API


def create_category(client, headers, name="Food", description=None):
    response = client.post(
        f"{API}/categories",
        json={"name": name, "description": description},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_create_and_list_categories(client, auth_headers):
    create_category(client, auth_headers, "Transport")
    create_category(client, auth_headers, "Food", "Groceries and eating out")

    response = client.get(f"{API}/categories", headers=auth_headers)

    assert response.status_code == 200
    # Sorted alphabetically by name.
    assert [category["name"] for category in response.json()] == ["Food", "Transport"]


def test_duplicate_category_name_is_rejected(client, auth_headers):
    create_category(client, auth_headers, "Food")

    response = client.post(
        f"{API}/categories", json={"name": "food"}, headers=auth_headers
    )

    assert response.status_code == 409


def test_two_users_can_use_the_same_category_name(client, auth_headers, other_user_headers):
    create_category(client, auth_headers, "Food")

    create_category(client, other_user_headers, "Food")  # asserts 201 inside


def test_update_category(client, auth_headers):
    category = create_category(client, auth_headers, "Fod")

    response = client.patch(
        f"{API}/categories/{category['id']}",
        json={"name": "Food"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Food"


def test_cannot_rename_category_to_an_existing_name(client, auth_headers):
    create_category(client, auth_headers, "Food")
    rent = create_category(client, auth_headers, "Rent")

    response = client.patch(
        f"{API}/categories/{rent['id']}", json={"name": "Food"}, headers=auth_headers
    )

    assert response.status_code == 409


def test_other_user_cannot_see_or_change_my_category(client, auth_headers, other_user_headers):
    category = create_category(client, auth_headers, "Food")
    url = f"{API}/categories/{category['id']}"

    assert client.get(url, headers=other_user_headers).status_code == 404
    assert client.patch(url, json={"name": "Hacked"}, headers=other_user_headers).status_code == 404
    assert client.delete(url, headers=other_user_headers).status_code == 404
    assert client.get(f"{API}/categories", headers=other_user_headers).json() == []


def test_deleting_category_keeps_expenses_as_uncategorized(client, auth_headers):
    category = create_category(client, auth_headers, "Food")
    expense = client.post(
        f"{API}/expenses",
        json={"title": "Lunch", "amount": "180.00", "category_id": category["id"]},
        headers=auth_headers,
    ).json()
    assert expense["category"]["name"] == "Food"

    response = client.delete(f"{API}/categories/{category['id']}", headers=auth_headers)
    assert response.status_code == 204

    expense_after = client.get(f"{API}/expenses/{expense['id']}", headers=auth_headers)
    assert expense_after.status_code == 200
    assert expense_after.json()["category"] is None
