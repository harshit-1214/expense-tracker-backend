"""
Schemas for expenses.

Amounts are `Decimal`, never `float`, so 0.1 + 0.2 style rounding errors
cannot creep into money. In JSON responses they appear as strings ("250.00").
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.models.expense import PaymentMethod
from app.schemas.category import CategorySummary

ExpenseTitle = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)
]
# Matches the Numeric(12, 2) column: positive, at most 2 decimal places.
MoneyAmount = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]


class ExpenseCreate(BaseModel):
    """Body of POST /expenses."""

    # Store "cash" (the plain string) instead of the PaymentMethod enum object.
    model_config = ConfigDict(use_enum_values=True)

    title: ExpenseTitle
    amount: MoneyAmount
    # Defaults to today when the client does not send a date.
    expense_date: date = Field(default_factory=date.today)
    payment_method: PaymentMethod = Field(
        default=PaymentMethod.CASH, validate_default=True
    )
    notes: str | None = Field(default=None, max_length=1000)
    # Leave out (or send null) for an uncategorized expense.
    category_id: int | None = None


class ExpenseUpdate(BaseModel):
    """Body of PATCH /expenses/{id}. Only the fields you send are changed."""

    model_config = ConfigDict(use_enum_values=True)

    title: ExpenseTitle | None = None
    amount: MoneyAmount | None = None
    expense_date: date | None = None
    payment_method: PaymentMethod | None = None
    notes: str | None = Field(default=None, max_length=1000)
    # Send null to remove the category from the expense.
    category_id: int | None = None

    @model_validator(mode="after")
    def required_fields_cannot_be_null(self) -> "ExpenseUpdate":
        # `notes` and `category_id` may be set to null; these columns may not.
        for field_name in ("title", "amount", "expense_date", "payment_method"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class ExpenseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    amount: Decimal
    expense_date: date
    payment_method: PaymentMethod
    notes: str | None
    category: CategorySummary | None
    created_at: datetime
    updated_at: datetime


class ExpenseListResponse(BaseModel):
    """One page of expenses plus what a client needs to build pagination."""

    items: list[ExpenseResponse]
    total: int  # how many expenses match the filters across all pages
    limit: int
    offset: int
