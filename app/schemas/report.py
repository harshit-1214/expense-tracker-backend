"""Schemas for the spending reports (response only - reports are read-only)."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class ExpenseSummary(BaseModel):
    """Overall totals for a date range. GET /reports/summary"""

    start_date: date | None
    end_date: date | None
    total_amount: Decimal
    expense_count: int
    average_amount: Decimal
    highest_amount: Decimal


class CategoryTotal(BaseModel):
    """Spending for one category. GET /reports/by-category"""

    category_id: int | None  # null for the "Uncategorized" row
    category_name: str
    total_amount: Decimal
    expense_count: int
    percentage_of_total: float


class MonthlyTotal(BaseModel):
    """Spending for one calendar month. GET /reports/monthly"""

    year: int
    month: int  # 1 = January ... 12 = December
    total_amount: Decimal
    expense_count: int
