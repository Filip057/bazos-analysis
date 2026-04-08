"""
Authentication module — JWT-based admin auth.

Provides password hashing (bcrypt), JWT token issuance/verification,
and a Flask decorator (`admin_required`) to protect admin endpoints.

Tokens expire after 24 hours; users must re-login daily.
"""
import logging
import os
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Optional

import bcrypt
import jwt
from flask import jsonify, request

logger = logging.getLogger(__name__)

# Token lifetime — user re-logs once per day
TOKEN_LIFETIME = timedelta(hours=24)
JWT_ALGORITHM = "HS256"


def _get_secret() -> str:
    """Return the JWT signing secret from env. Raises if missing."""
    secret = os.getenv("JWT_SECRET")
    if not secret:
        raise RuntimeError("JWT_SECRET must be set in .env")
    return secret


def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify plaintext password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def issue_token(admin_id: int, username: str) -> str:
    """Create a signed JWT for the given admin."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(admin_id),
        "username": username,
        "iat": now,
        "exp": now + TOKEN_LIFETIME,
    }
    return jwt.encode(payload, _get_secret(), algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """
    Decode and validate a JWT. Returns payload dict or None if invalid/expired.
    """
    try:
        return jwt.decode(token, _get_secret(), algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        logger.info("Auth: token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.info(f"Auth: invalid token ({e})")
        return None


def _extract_token() -> Optional[str]:
    """Pull bearer token from the Authorization header."""
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        return header[7:].strip()
    return None


def admin_required(fn):
    """
    Decorator: reject requests without a valid admin JWT.

    On success, attaches the decoded payload to flask.g via request context.
    On failure, returns 401 JSON error.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = _extract_token()
        if not token:
            return jsonify({"error": "Authentication required"}), 401

        payload = decode_token(token)
        if not payload:
            return jsonify({"error": "Invalid or expired token"}), 401

        request.admin = payload  # type: ignore[attr-defined]
        return fn(*args, **kwargs)

    return wrapper
