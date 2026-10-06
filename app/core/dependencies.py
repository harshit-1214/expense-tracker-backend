"""
Reusable FastAPI dependencies.

Routers import the `Annotated` aliases defined here instead of repeating
`Depends(...)` in every endpoint:

    def list_expenses(db: DatabaseSession, current_user: CurrentUser): ...
"""

from dataclasses import dataclass
from datetime import date
from typing import Annotated

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_access_token
from app.database.session import get_db
from app.models.user import User

# Tells Swagger UI (/docs) where to send the login form to get a token.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")

# One database session per request.
DatabaseSession = Annotated[Session, Depends(get_db)]


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: DatabaseSession,
) -> User:
    """Read the Bearer token and return the logged-in user, or respond 401."""
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    user_id = decode_access_token(token)
    if user_id is None:
        raise credentials_error

    user = db.get(User, user_id)
    # The token can outlive the account (deleted or deactivated user).
    if user is None or not user.is_active:
        raise credentials_error

    return user


# Any endpoint that declares this parameter requires a valid login.
CurrentUser = Annotated[User, Depends(get_current_user)]


# ---------------------------------------------------------------------------
# Shared query filters
# ---------------------------------------------------------------------------
@dataclass
class DateRange:
    start_date: date | None
    end_date: date | None


def get_date_range(
    start_date: Annotated[
        date | None,
        Query(description="Only include expenses on or after this date (YYYY-MM-DD)"),
    ] = None,
    end_date: Annotated[
        date | None,
        Query(description="Only include expenses on or before this date (YYYY-MM-DD)"),
    ] = None,
) -> DateRange:
    """Optional ?start_date=&end_date= filter shared by expenses and reports."""
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="start_date must be on or before end_date",
        )
    return DateRange(start_date=start_date, end_date=end_date)


DateRangeFilter = Annotated[DateRange, Depends(get_date_range)]
