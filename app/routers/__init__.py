"""
routers/ - The API endpoints, one file per resource.

    health.py      -> GET /health (is the API and database up?)
    auth.py        -> register and login
    users.py       -> the logged-in user's profile
    categories.py  -> CRUD for expense categories
    expenses.py    -> CRUD for expenses, with filtering and pagination
    reports.py     -> spending summaries (totals, by category, by month)

Each file exposes a `router` object that app/main.py registers.
"""
