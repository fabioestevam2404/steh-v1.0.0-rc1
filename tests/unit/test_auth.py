from datetime import datetime, timedelta, timezone
import jwt
import pytest
from fastapi import HTTPException

from app.core import auth

def test_local_mode_returns_development_principal(monkeypatch):
    monkeypatch.setattr(auth.settings, "auth_enabled", False)
    p=auth.get_principal(None)
    assert "steh_user" in p.roles

def test_auth_enabled_rejects_missing_token(monkeypatch):
    monkeypatch.setattr(auth.settings, "auth_enabled", True)
    with pytest.raises(HTTPException) as exc:
        auth.get_principal(None)
    assert exc.value.status_code == 401

def test_role_is_required(monkeypatch):
    monkeypatch.setattr(auth.settings, "auth_enabled", True)
    monkeypatch.setattr(auth.settings, "auth_jwt_secret", "test-secret")
    token=jwt.encode(
        {"sub":"user","roles":["reader"],"exp":datetime.now(timezone.utc)+timedelta(minutes=5)},
        "test-secret", algorithm="HS256"
    )
    with pytest.raises(HTTPException) as exc:
        auth.get_principal("Bearer "+token)
    assert exc.value.status_code == 403
