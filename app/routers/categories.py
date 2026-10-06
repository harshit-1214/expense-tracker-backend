"""
Category endpoints.

Every query is filtered by `owner_id`, so users can only ever see and
change their own categories.
"""

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.dependencies import CurrentUser, DatabaseSession
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate

router = APIRouter(prefix="/categories", tags=["Categories"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def get_owned_category_or_404(db: Session, category_id: int, owner_id: int) -> Category:
    """
    Fetch a category that belongs to the user.

    Someone else's category gives the same 404 as a missing one, so the API
    never reveals which ids exist for other users.
    """
    category = db.scalar(
        select(Category).where(
            Category.id == category_id, Category.owner_id == owner_id
        )
    )
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )
    return category


def ensure_category_name_is_unique(
    db: Session, owner_id: int, name: str, ignore_category_id: int | None = None
) -> None:
    """Respond 409 if the user already has a category with this name ("Food" == "food")."""
    query = select(Category.id).where(
        Category.owner_id == owner_id,
        func.lower(Category.name) == name.lower(),
    )
    if ignore_category_id is not None:
        # When renaming, the category must not conflict with itself.
        query = query.where(Category.id != ignore_category_id)

    if db.scalar(query) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"You already have a category named '{name}'",
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.post(
    "",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a category",
)
def create_category(
    category_in: CategoryCreate, db: DatabaseSession, current_user: CurrentUser
) -> Category:
    ensure_category_name_is_unique(db, current_user.id, category_in.name)

    category = Category(**category_in.model_dump(), owner_id=current_user.id)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.get("", response_model=list[CategoryResponse], summary="List my categories")
def list_categories(db: DatabaseSession, current_user: CurrentUser) -> list[Category]:
    categories = db.scalars(
        select(Category)
        .where(Category.owner_id == current_user.id)
        .order_by(Category.name)
    )
    return list(categories)


@router.get("/{category_id}", response_model=CategoryResponse, summary="Get one category")
def get_category(
    category_id: int, db: DatabaseSession, current_user: CurrentUser
) -> Category:
    return get_owned_category_or_404(db, category_id, current_user.id)


@router.patch("/{category_id}", response_model=CategoryResponse, summary="Update a category")
def update_category(
    category_id: int,
    category_in: CategoryUpdate,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> Category:
    category = get_owned_category_or_404(db, category_id, current_user.id)

    # exclude_unset=True -> only the fields the client actually sent.
    changes = category_in.model_dump(exclude_unset=True)
    if "name" in changes:
        ensure_category_name_is_unique(
            db, current_user.id, changes["name"], ignore_category_id=category.id
        )

    for field_name, value in changes.items():
        setattr(category, field_name, value)

    db.commit()
    db.refresh(category)
    return category


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a category",
)
def delete_category(
    category_id: int, db: DatabaseSession, current_user: CurrentUser
) -> Response:
    """The category's expenses are kept and become uncategorized."""
    category = get_owned_category_or_404(db, category_id, current_user.id)
    db.delete(category)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
