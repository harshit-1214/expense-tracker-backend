"""Authentication endpoints: create an account and log in."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.dependencies import DatabaseSession
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import Token
from app.schemas.user import UserCreate, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new account",
)
def register_user(user_in: UserCreate, db: DatabaseSession) -> User:
    email_already_registered = HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="An account with this email already exists",
    )

    email = user_in.email.lower()
    if db.scalar(select(User).where(User.email == email)) is not None:
        raise email_already_registered

    user = User(
        email=email,
        full_name=user_in.full_name,
        hashed_password=hash_password(user_in.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # Two requests registered the same email at the same moment;
        # the unique index on users.email caught the second one.
        db.rollback()
        raise email_already_registered
    db.refresh(user)
    return user


@router.post("/login", response_model=Token, summary="Log in and get an access token")
def login(
    credentials: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DatabaseSession,
) -> Token:
    """
    Send the email in the `username` form field (OAuth2 standard) and the
    password in `password`. The Authorize button in /docs uses this endpoint.
    """
    user = db.scalar(select(User).where(User.email == credentials.username.lower()))

    # Same error for "no such email" and "wrong password", so an attacker
    # cannot use this endpoint to discover which emails are registered.
    if (
        user is None
        or not user.is_active
        or not verify_password(credentials.password, user.hashed_password)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return Token(access_token=create_access_token(user.id))
