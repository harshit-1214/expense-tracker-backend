"""`categories` table: a user's own labels for grouping expenses (Food, Rent...)."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.expense import Expense
    from app.models.user import User


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (
        # A user cannot have two categories with the same name,
        # but two different users can both have "Food".
        UniqueConstraint("owner_id", "name", name="uq_categories_owner_id_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(String(255))
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    owner: Mapped["User"] = relationship(back_populates="categories")
    # Deleting a category keeps its expenses: the database sets their
    # category_id to NULL (see ON DELETE SET NULL in models/expense.py).
    expenses: Mapped[list["Expense"]] = relationship(
        back_populates="category", passive_deletes=True
    )
