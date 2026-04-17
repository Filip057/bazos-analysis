"""
Tests for the admin auth module — password hashing, JWT, and protection.

Covers:
1. hash_password / verify_password (bcrypt round-trip)
2. issue_token / decode_token (JWT validity, expiry, tampering)
3. admin_required decorator (401 on missing/invalid token, 200 on valid)
"""
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import jwt
import pytest
from flask import Flask, jsonify

# Ensure JWT_SECRET is set before importing the auth module
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-unit-tests-min-32-bytes")

from webapp.auth import (
    JWT_ALGORITHM,
    admin_required,
    decode_token,
    hash_password,
    issue_token,
    verify_password,
)


class TestJWTSecretValidation:
    """Startup-time validation of JWT_SECRET length and presence."""

    def _reload_secret(self):
        """Helper: re-import _get_secret so it picks up patched env."""
        from webapp.auth import _get_secret
        return _get_secret

    def test_missing_secret_raises(self):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(RuntimeError, match="JWT_SECRET must be set"):
                self._reload_secret()()

    def test_short_secret_rejected(self):
        # 31 bytes — one short of the HS256 minimum
        short = "a" * 31
        with patch.dict(os.environ, {"JWT_SECRET": short}):
            with pytest.raises(RuntimeError, match="at least 32 bytes"):
                self._reload_secret()()

    def test_minimum_length_secret_accepted(self):
        # Exactly 32 bytes — should pass
        ok = "a" * 32
        with patch.dict(os.environ, {"JWT_SECRET": ok}):
            assert self._reload_secret()() == ok


class TestPasswordHashing:
    """bcrypt password hashing round-trip."""

    def test_hash_and_verify_correct_password(self):
        h = hash_password("hunter2-strong")
        assert verify_password("hunter2-strong", h) is True

    def test_verify_rejects_wrong_password(self):
        h = hash_password("correct-horse")
        assert verify_password("wrong-horse", h) is False

    def test_hash_is_not_plaintext(self):
        password = "supersecret"
        h = hash_password(password)
        assert password not in h
        assert h.startswith("$2")  # bcrypt prefix

    def test_each_hash_is_unique(self):
        # bcrypt uses random salt — same input → different hash
        assert hash_password("same") != hash_password("same")

    def test_verify_handles_garbage_hash(self):
        assert verify_password("anything", "not-a-real-hash") is False


class TestJWTTokens:
    """JWT issuance and decoding."""

    def test_issue_and_decode_round_trip(self):
        token = issue_token(admin_id=42, username="filip")
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "42"
        assert payload["username"] == "filip"
        assert "exp" in payload

    def test_decode_rejects_tampered_token(self):
        token = issue_token(admin_id=1, username="admin")
        tampered = token[:-5] + "XXXXX"
        assert decode_token(tampered) is None

    def test_decode_rejects_expired_token(self):
        # Manually craft an expired token using the same secret
        secret = os.environ["JWT_SECRET"]
        expired = jwt.encode(
            {
                "sub": "1",
                "username": "admin",
                "iat": datetime.now(timezone.utc) - timedelta(hours=48),
                "exp": datetime.now(timezone.utc) - timedelta(hours=24),
            },
            secret,
            algorithm=JWT_ALGORITHM,
        )
        assert decode_token(expired) is None

    def test_decode_rejects_wrong_secret(self):
        # Token signed by a different secret should fail
        bogus = jwt.encode({"sub": "1"}, "different-secret-padded-to-32-bytes!", algorithm=JWT_ALGORITHM)
        assert decode_token(bogus) is None


class TestAdminRequiredDecorator:
    """End-to-end test of @admin_required via a tiny Flask app."""

    @pytest.fixture
    def client(self):
        app = Flask(__name__)

        @app.route("/protected")
        @admin_required
        def protected():
            return jsonify({"ok": True})

        return app.test_client()

    def test_no_token_returns_401(self, client):
        resp = client.get("/protected")
        assert resp.status_code == 401
        assert "error" in resp.get_json()

    def test_malformed_header_returns_401(self, client):
        resp = client.get("/protected", headers={"Authorization": "NotBearer xyz"})
        assert resp.status_code == 401

    def test_invalid_token_returns_401(self, client):
        resp = client.get(
            "/protected", headers={"Authorization": "Bearer total.garbage.token"}
        )
        assert resp.status_code == 401

    def test_valid_token_returns_200(self, client):
        token = issue_token(admin_id=1, username="filip")
        resp = client.get(
            "/protected", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        assert resp.get_json() == {"ok": True}

    def test_expired_token_returns_401(self, client):
        secret = os.environ["JWT_SECRET"]
        expired = jwt.encode(
            {
                "sub": "1",
                "username": "admin",
                "iat": datetime.now(timezone.utc) - timedelta(hours=48),
                "exp": datetime.now(timezone.utc) - timedelta(hours=24),
            },
            secret,
            algorithm=JWT_ALGORITHM,
        )
        resp = client.get(
            "/protected", headers={"Authorization": f"Bearer {expired}"}
        )
        assert resp.status_code == 401
