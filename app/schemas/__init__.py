"""
schemas/ - Pydantic models that define what the API accepts and returns.

Models (app/models) describe database tables; schemas describe JSON.
Keeping them separate means a column like `hashed_password` can never
leak into a response by accident.

    auth.py      -> login token response
    user.py      -> register request and user profile response
    category.py  -> category create / update / response
    expense.py   -> expense create / update / response and the paginated list
    report.py    -> spending summary responses
"""
