"""Schemas for authentication responses."""

from pydantic import BaseModel


class Token(BaseModel):
    """Returned by POST /auth/login. Send it back as `Authorization: Bearer <token>`."""

    access_token: str
    token_type: str = "bearer"
