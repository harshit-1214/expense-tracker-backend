"""
Security helpers: password hashing and JWT access tokens.

Nothing in this file talks to the database or to FastAPI, which keeps it
easy to test and reuse.
"""

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from pwdlib import PasswordHash

from app.core.config import settings

# Argon2id with safe default settings.
password_hasher = PasswordHash.recommended()


# ---------------------------------------------------------------------------
# Passwords
# ---------------------------------------------------------------------------
def hash_password(plain_password: str) -> str:
    """Return a salted hash that is safe to store in the database."""
    return password_hasher.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a login password against the stored hash."""
    return password_hasher.verify(plain_password, hashed_password)


# ---------------------------------------------------------------------------
# JWT access tokens
# ---------------------------------------------------------------------------
def create_access_token(user_id: int) -> str:
    """Create a signed JWT that identifies the user until it expires."""
    # Always use UTC: the "exp" claim is compared against UTC when decoding.
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": str(user_id),  # "sub" (subject) is the standard claim for the user
        "exp": expires_at,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> int | None:
    """
    Return the user id stored in the token.

    Returns None when the token is invalid, tampered with, or expired.
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return int(payload["sub"])
    except (JWTError, KeyError, TypeError, ValueError):
        return None
