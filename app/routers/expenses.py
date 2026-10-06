"""
Expense endpoints: create, list (with filters + pagination), read, update, delete.

Every query is filtered by `owner_id`, so users can only ever see and
change their own expenses.
"""

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.dependencies import CurrentUser, DatabaseSession, DateRangeFilter
from app.models.expense import Expense, PaymentMethod
from app.routers.categories import get_owned_category_or_404
from app.schemas.expense import (
    ExpenseCreate,
    ExpenseListResponse,
    ExpenseResponse,
    ExpenseUpdate,
)

router = APIRouter(prefix="/expenses", tags=["Expenses"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def get_owned_expense_or_404(db: Session, expense_id: int, owner_id: int) -> Expense:
    """Fetch an expense that belongs to the user, or respond 404."""
    expense = db.scalar(
        select(Expense).where(Expense.id == expense_id, Expense.owner_id == owner_id)
    )
    if expense is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found"
        )
    return expense


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.post(
    "",
    response_model=ExpenseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an expense",
)
def create_expense(
    expense_in: ExpenseCreate, db: DatabaseSession, current_user: CurrentUser
) -> Expense:
    if expense_in.category_id is not None:
        # Stops a user from attaching their expense to someone else's category.
        get_owned_category_or_404(db, expense_in.category_id, current_user.id)

    expense = Expense(**expense_in.model_dump(), owner_id=current_user.id)
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


@router.get("", response_model=ExpenseListResponse, summary="List my expenses")
def list_expenses(
    db: DatabaseSession,
    current_user: CurrentUser,
    date_range: DateRangeFilter,
    category_id: Annotated[
        int | None, Query(description="Only expenses in this category")
    ] = None,
    payment_method: Annotated[
        PaymentMethod | None, Query(description="Only expenses paid this way")
    ] = None,
    min_amount: Annotated[Decimal | None, Query(ge=0)] = None,
    max_amount: Annotated[Decimal | None, Query(ge=0)] = None,
    search: Annotated[
        str | None,
        Query(max_length=150, description="Text to look for in the title (case-insensitive)"),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Page size")] = 20,
    offset: Annotated[int, Query(ge=0, description="How many expenses to skip")] = 0,
) -> ExpenseListResponse:
    # Build the WHERE conditions once; they are shared by the count query
    # and the page query below.
    filters = [Expense.owner_id == current_user.id]
    if date_range.start_date is not None:
        filters.append(Expense.expense_date >= date_range.start_date)
    if date_range.end_date is not None:
        filters.append(Expense.expense_date <= date_range.end_date)
    if category_id is not None:
        filters.append(Expense.category_id == category_id)
    if payment_method is not None:
        filters.append(Expense.payment_method == payment_method.value)
    if min_amount is not None:
        filters.append(Expense.amount >= min_amount)
    if max_amount is not None:
        filters.append(Expense.amount <= max_amount)
    if search:
        # autoescape=True treats % and _ typed by the user as normal characters.
        filters.append(Expense.title.icontains(search, autoescape=True))

    total = db.scalar(select(func.count()).select_from(Expense).where(*filters))

    expenses = db.scalars(
        select(Expense)
        # Load all categories for the page in one extra query (avoids N+1).
        .options(selectinload(Expense.category))
        .where(*filters)
        # Newest first; id breaks ties so pages never overlap.
        .order_by(Expense.expense_date.desc(), Expense.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()

    return ExpenseListResponse(items=expenses, total=total, limit=limit, offset=offset)


@router.get("/{expense_id}", response_model=ExpenseResponse, summary="Get one expense")
def get_expense(
    expense_id: int, db: DatabaseSession, current_user: CurrentUser
) -> Expense:
    return get_owned_expense_or_404(db, expense_id, current_user.id)


@router.patch("/{expense_id}", response_model=ExpenseResponse, summary="Update an expense")
def update_expense(
    expense_id: int,
    expense_in: ExpenseUpdate,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> Expense:
    expense = get_owned_expense_or_404(db, expense_id, current_user.id)

    # exclude_unset=True -> only the fields the client actually sent.
    changes = expense_in.model_dump(exclude_unset=True)
    if changes.get("category_id") is not None:
        get_owned_category_or_404(db, changes["category_id"], current_user.id)

    for field_name, value in changes.items():
        setattr(expense, field_name, value)

    db.commit()
    db.refresh(expense)
    return expense


@router.delete(
    "/{expense_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an expense",
)
def delete_expense(
    expense_id: int, db: DatabaseSession, current_user: CurrentUser
) -> Response:
    expense = get_owned_expense_or_404(db, expense_id, current_user.id)
    db.delete(expense)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
