from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi import HTTPException

from app.core import auth

TEST_JWT_SECRET = "test-secret-with-at-least-32-bytes"


def test_local_mode_returns_development_principal(monkeypatch):
    monkeypatch.setattr(auth.settings, "auth_enabled", False)
    p = auth.get_principal(None)
    assert "steh_user" in p.roles
    assert "steh_reviewer" in p.roles


def test_reviewer_role_is_required(monkeypatch):
    monkeypatch.setattr(auth.settings, "auth_reviewer_role", "steh_reviewer")
    principal = auth.Principal(subject="user", roles=("steh_user",))

    with pytest.raises(HTTPException) as exc:
        auth.require_reviewer(principal)

    assert exc.value.status_code == 403


def test_auth_enabled_rejects_missing_token(monkeypatch):
    monkeypatch.setattr(auth.settings, "auth_enabled", True)
    with pytest.raises(HTTPException) as exc:
        auth.get_principal(None)
    assert exc.value.status_code == 401


def test_role_is_required(monkeypatch):
    monkeypatch.setattr(auth.settings, "auth_enabled", True)
    monkeypatch.setattr(auth.settings, "auth_jwt_secret", TEST_JWT_SECRET)
    token = jwt.encode(
        {
            "sub": "user",
            "roles": ["reader"],
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        TEST_JWT_SECRET,
        algorithm="HS256",
    )
    with pytest.raises(HTTPException) as exc:
        auth.get_principal("Bearer " + token)
    assert exc.value.status_code == 403
