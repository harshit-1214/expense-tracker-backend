"""
Report endpoints: read-only summaries of the logged-in user's spending.

The totals are calculated by the database (SUM / COUNT / GROUP BY), not in
Python, so they stay fast even with thousands of expenses.
"""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import extract, func, select

from app.core.dependencies import CurrentUser, DatabaseSession, DateRange, DateRangeFilter
from app.models.category import Category
from app.models.expense import Expense
from app.schemas.report import CategoryTotal, ExpenseSummary, MonthlyTotal

router = APIRouter(prefix="/reports", tags=["Reports"])

UNCATEGORIZED_LABEL = "Uncategorized"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def to_money(value: Decimal | float | int | None) -> Decimal:
    """Round a database aggregate to 2 decimal places (None becomes 0.00)."""
    return Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def build_expense_filters(owner_id: int, date_range: DateRange) -> list:
    """WHERE conditions shared by the reports: the user's expenses in the date range."""
    filters = [Expense.owner_id == owner_id]
    if date_range.start_date is not None:
        filters.append(Expense.expense_date >= date_range.start_date)
    if date_range.end_date is not None:
        filters.append(Expense.expense_date <= date_range.end_date)
    return filters


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.get("/summary", response_model=ExpenseSummary, summary="Overall spending totals")
def get_expense_summary(
    db: DatabaseSession, current_user: CurrentUser, date_range: DateRangeFilter
) -> ExpenseSummary:
    total_amount, expense_count, average_amount, highest_amount = db.execute(
        select(
            func.sum(Expense.amount),
            func.count(Expense.id),
            func.avg(Expense.amount),
            func.max(Expense.amount),
        ).where(*build_expense_filters(current_user.id, date_range))
    ).one()

    return ExpenseSummary(
        start_date=date_range.start_date,
        end_date=date_range.end_date,
        total_amount=to_money(total_amount),
        expense_count=expense_count,
        average_amount=to_money(average_amount),
        highest_amount=to_money(highest_amount),
    )


@router.get(
    "/by-category",
    response_model=list[CategoryTotal],
    summary="Spending grouped by category",
)
def get_spending_by_category(
    db: DatabaseSession, current_user: CurrentUser, date_range: DateRangeFilter
) -> list[CategoryTotal]:
    """Biggest category first. Expenses without a category are grouped as "Uncategorized"."""
    total_amount = func.sum(Expense.amount)
    rows = db.execute(
        select(
            Category.id,
            Category.name,
            total_amount.label("total_amount"),
            func.count(Expense.id).label("expense_count"),
        )
        .select_from(Expense)
        # OUTER join keeps expenses whose category_id is NULL.
        .outerjoin(Category, Expense.category_id == Category.id)
        .where(*build_expense_filters(current_user.id, date_range))
        .group_by(Category.id, Category.name)
        .order_by(total_amount.desc())
    ).all()

    grand_total = sum((to_money(row.total_amount) for row in rows), Decimal("0"))

    return [
        CategoryTotal(
            category_id=row.id,
            category_name=row.name or UNCATEGORIZED_LABEL,
            total_amount=to_money(row.total_amount),
            expense_count=row.expense_count,
            percentage_of_total=round(
                float(to_money(row.total_amount) / grand_total * 100), 2
            ),
        )
        for row in rows
    ]


@router.get(
    "/monthly",
    response_model=list[MonthlyTotal],
    summary="Spending for each month of a year",
)
def get_monthly_spending(
    db: DatabaseSession,
    current_user: CurrentUser,
    year: Annotated[
        int | None,
        Query(ge=2000, le=2100, description="Defaults to the current year"),
    ] = None,
) -> list[MonthlyTotal]:
    """Always returns 12 rows (January to December) so charts need no gap-filling."""
    year = year or date.today().year
    month = extract("month", Expense.expense_date)

    rows = db.execute(
        select(
            month.label("month"),
            func.sum(Expense.amount).label("total_amount"),
            func.count(Expense.id).label("expense_count"),
        )
        .where(
            Expense.owner_id == current_user.id,
            # A date range (instead of extract(year) = ...) lets the database
            # use the (owner_id, expense_date) index.
            Expense.expense_date >= date(year, 1, 1),
            Expense.expense_date <= date(year, 12, 31),
        )
        .group_by(month)
    ).all()

    totals_by_month = {int(row.month): row for row in rows}

    monthly_totals = []
    for month_number in range(1, 13):
        row = totals_by_month.get(month_number)
        monthly_totals.append(
            MonthlyTotal(
                year=year,
                month=month_number,
                total_amount=to_money(row.total_amount if row else 0),
                expense_count=row.expense_count if row else 0,
            )
        )
    return monthly_totals
