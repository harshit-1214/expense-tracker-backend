"""
tests/ - Automated tests for the API (run with `pytest`).

    conftest.py         -> shared fixtures: test database, API client, logged-in users
    test_auth.py        -> register, login and token protection
    test_categories.py  -> category CRUD and ownership rules
    test_expenses.py    -> expense CRUD, filters, pagination and ownership rules
    test_reports.py     -> summary, by-category and monthly reports

The tests run against a temporary in-memory SQLite database, so they never
touch your real PostgreSQL data.
"""
