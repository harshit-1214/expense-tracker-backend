"""Endpoints about the logged-in user's own account."""

from fastapi import APIRouter

from app.core.dependencies import CurrentUser
from app.models.user import User
from app.schemas.user import UserResponse

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse, summary="Get my profile")
def get_my_profile(current_user: CurrentUser) -> User:
    return current_user
