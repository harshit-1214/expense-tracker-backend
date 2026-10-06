"""
models/ - Database tables, written as SQLAlchemy ORM models (one file per table).

    user.py      -> `users` table: accounts that can log in
    category.py  -> `categories` table: each user's own expense categories
    expense.py   -> `expenses` table: the money a user spent

Every model is imported here so that `import app.models` registers all the
tables on `Base.metadata`. Alembic relies on that for autogenerate.
"""

from app.models.category import Category
from app.models.expense import Expense, PaymentMethod
from app.models.user import User

__all__ = ["Category", "Expense", "PaymentMethod", "User"]
