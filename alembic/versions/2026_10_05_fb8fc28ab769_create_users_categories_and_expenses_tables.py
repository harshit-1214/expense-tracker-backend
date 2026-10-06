"""create users, categories and expenses tables

The first migration: builds the whole initial schema.

Revision ID: fb8fc28ab769
Revises:
Create Date: 2026-10-05 17:28:12.663537

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fb8fc28ab769'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # users: accounts that can log in. Created first because the other
    # two tables point at it with foreign keys.
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=100), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
    )
    # Unique index: no two accounts with the same email, and fast login lookups.
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # categories: each user's own labels (Food, Rent...).
    op.create_table(
        'categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        # Deleting a user deletes their categories.
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], name=op.f('fk_categories_owner_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_categories')),
        # A user cannot have two categories with the same name.
        sa.UniqueConstraint('owner_id', 'name', name='uq_categories_owner_id_name'),
    )
    op.create_index(op.f('ix_categories_owner_id'), 'categories', ['owner_id'], unique=False)

    # expenses: one row for each time a user spent money.
    op.create_table(
        'expenses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=150), nullable=False),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('expense_date', sa.Date(), nullable=False),
        sa.Column('payment_method', sa.String(length=20), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint('amount > 0', name=op.f('ck_expenses_amount_positive')),
        # Deleting a category keeps its expenses as "uncategorized".
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], name=op.f('fk_expenses_category_id_categories'), ondelete='SET NULL'),
        # Deleting a user deletes their expenses.
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], name=op.f('fk_expenses_owner_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_expenses')),
    )
    op.create_index(op.f('ix_expenses_category_id'), 'expenses', ['category_id'], unique=False)
    # Speeds up "this user's expenses in a date range" (lists and reports).
    op.create_index('ix_expenses_owner_id_expense_date', 'expenses', ['owner_id', 'expense_date'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Reverse order of upgrade(): tables with foreign keys are dropped first.
    op.drop_index('ix_expenses_owner_id_expense_date', table_name='expenses')
    op.drop_index(op.f('ix_expenses_category_id'), table_name='expenses')
    op.drop_table('expenses')
    op.drop_index(op.f('ix_categories_owner_id'), table_name='categories')
    op.drop_table('categories')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
