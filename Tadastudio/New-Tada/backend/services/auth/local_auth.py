"""Local email/password authentication service.

Manages locally-created user accounts for external users who don't have
a Microsoft Entra identity. Passwords are stored as bcrypt hashes and
sessions are issued as HS256 JWTs stored in an HttpOnly cookie.
"""

import logging
import os
import time
from typing import Any, Dict, Optional

import bcrypt
import jwt as pyjwt

from backend.models.auth.local_user import LocalUser
from backend.services.auth.config import get_auth_config
from backend.services.database import get_db

logger = logging.getLogger(__name__)

# Feature flag -- set ENABLE_LOCAL_AUTH=true to activate email/password auth.
# Defaults to false so the app behaves identically to the original Entra-only setup.
LOCAL_AUTH_ENABLED: bool = os.getenv("ENABLE_LOCAL_AUTH", "false").lower() in {"1", "true", "yes"}

_LOCAL_AUTH_AUDIENCE = "local-auth"
_LOCAL_AUTH_ISSUER = "agenticstudio"
_LOCAL_JWT_EXPIRY_SECONDS = 7 * 24 * 3600  # 7 days


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _check_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------


def create_local_user(email: str, password: str) -> LocalUser:
    """Create a new local user account.

    Raises:
        ValueError: If a user with that email already exists.
    """
    email = email.strip().lower()
    with get_db() as db:
        existing = db.query(LocalUser).filter(LocalUser.email == email).first()
        if existing:
            raise ValueError(f"A local user with email '{email}' already exists.")
        user = LocalUser(email=email, hashed_password=_hash_password(password))
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"[LOCAL-AUTH] Created local user: {email}")
        return user


def get_local_users() -> list[LocalUser]:
    """Return all local user records (active and inactive)."""
    with get_db() as db:
        return db.query(LocalUser).order_by(LocalUser.created_at).all()


def get_local_user_by_id(user_id: str) -> Optional[LocalUser]:
    """Fetch a local user by primary key."""
    with get_db() as db:
        return db.query(LocalUser).filter(LocalUser.id == user_id).first()


def deactivate_local_user(user_id: str) -> bool:
    """Deactivate (soft-disable) a local user. Returns True if found."""
    with get_db() as db:
        user = db.query(LocalUser).filter(LocalUser.id == user_id).first()
        if not user:
            return False
        user.is_active = False
        db.commit()
        logger.info(f"[LOCAL-AUTH] Deactivated local user id={user_id}")
        return True


def reset_local_user_password(user_id: str, new_password: str) -> bool:
    """Update the password for a local user. Returns True if found."""
    with get_db() as db:
        user = db.query(LocalUser).filter(LocalUser.id == user_id).first()
        if not user:
            return False
        user.hashed_password = _hash_password(new_password)
        db.commit()
        logger.info(f"[LOCAL-AUTH] Password reset for local user id={user_id}")
        return True


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


def verify_local_user(email: str, password: str) -> Optional[LocalUser]:
    """Verify email/password credentials.

    Returns the LocalUser on success, None on failure (wrong credentials
    or inactive account).
    """
    email = email.strip().lower()
    with get_db() as db:
        user = (
            db.query(LocalUser)
            .filter(LocalUser.email == email, LocalUser.is_active == True)  # noqa: E712
            .first()
        )
        if user and _check_password(password, user.hashed_password):
            return user
    return None


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------


def create_local_jwt(email: str) -> str:
    """Issue a signed JWT for a local user session (7-day expiry)."""
    config = get_auth_config()
    now = int(time.time())
    payload = {
        "sub": email,
        "email": email,
        "auth_source": "local_password",
        "iss": _LOCAL_AUTH_ISSUER,
        "aud": _LOCAL_AUTH_AUDIENCE,
        "iat": now,
        "exp": now + _LOCAL_JWT_EXPIRY_SECONDS,
    }
    return pyjwt.encode(payload, config.jwt_secret, algorithm="HS256")


def validate_local_jwt(token: str) -> Optional[Dict[str, Any]]:
    """Validate a local auth JWT. Returns claims dict or None."""
    config = get_auth_config()
    try:
        claims = pyjwt.decode(
            token,
            config.jwt_secret,
            algorithms=["HS256"],
            audience=_LOCAL_AUTH_AUDIENCE,
            issuer=_LOCAL_AUTH_ISSUER,
        )
        return claims
    except pyjwt.ExpiredSignatureError:
        logger.debug("[LOCAL-AUTH] JWT expired")
    except pyjwt.InvalidTokenError as exc:
        logger.debug(f"[LOCAL-AUTH] Invalid JWT: {exc}")
    return None
