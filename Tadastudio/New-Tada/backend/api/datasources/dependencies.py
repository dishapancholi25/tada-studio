"""FastAPI dependencies for datasources API."""

from typing import Any, Dict

from fastapi import HTTPException

from backend.services.database import SessionLocal, get_db
from backend.models import User


def get_database():
    """Provide database session for dependency injection.

    Yields a SQLAlchemy session and ensures proper cleanup.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_user_id_from_claims(current_user: Dict[str, Any]) -> str:
    """Extract user_id from JWT claims.

    For OAuth users, uses sub directly or looks up by email.

    Args:
        current_user: Current user claims from JWT

    Returns:
        User ID string

    Raises:
        HTTPException: If user not found
    """
    email = current_user.get("email")
    sub = current_user.get("sub")

    with get_db() as db:
        # Try User by sub
        if sub:
            user = db.query(User).filter(User.id == sub).first()
            if user:
                return user.id

        # Try by email
        if email:
            user = db.query(User).filter(User.email == email).first()
            if user:
                return user.id

    raise HTTPException(status_code=401, detail="User not found")
