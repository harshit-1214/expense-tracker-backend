"""`expenses` table: one row for each time the user spent money."""

import enum
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.user import User


class PaymentMethod(str, enum.Enum):
    """How the expense was paid. Stored in the database as plain text."""

    CASH = "cash"
    CARD = "card"
    UPI = "upi"
    BANK_TRANSFER = "bank_transfer"
    OTHER = "other"


class Expense(Base):
    __tablename__ = "expenses"
    __table_args__ = (
        # Last line of defence: the API validates this too, but the database
        # must never hold a zero or negative expense.
        CheckConstraint("amount > 0", name="amount_positive"),
        # Almost every query is "this user's expenses in a date range".
        Index("ix_expenses_owner_id_expense_date", "owner_id", "expense_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(150))
    # Numeric (not Float) so money is stored exactly: up to 9,999,999,999.99
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    # The day the money was spent - can differ from created_at.
    expense_date: Mapped[date] = mapped_column(Date)
    payment_method: Mapped[str] = mapped_column(
        String(20), default=PaymentMethod.CASH.value
    )
    notes: Mapped[str | None] = mapped_column(Text)

    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    # NULL means "uncategorized".
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    owner: Mapped["User"] = relationship(back_populates="expenses")
    category: Mapped["Category | None"] = relationship(back_populates="expenses")
