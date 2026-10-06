"""`users` table: an account that owns categories and expenses."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String, func, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.expense import Expense


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Stored lowercase so "A@x.com" and "a@x.com" are the same account.
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(100))
    # Never the plain password - only the Argon2 hash.
    hashed_password: Mapped[str] = mapped_column(String(255))
    # Set to False to block a user from logging in without deleting their data.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # passive_deletes=True lets the database's ON DELETE CASCADE remove the
    # rows instead of SQLAlchemy loading and deleting them one by one.
    categories: Mapped[list["Category"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan", passive_deletes=True
    )
    expenses: Mapped[list["Expense"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan", passive_deletes=True
    )
