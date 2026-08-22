import asyncio

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from freeai.config import get_settings
from freeai.gateway.auth import verify_bearer_token


def test_auth_open_access_when_no_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "FREEAI_API_KEY", "")

    result = asyncio.run(verify_bearer_token(None))
    assert result == ""


def test_auth_valid_bearer_token(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "FREEAI_API_KEY", "secret_key_123")

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="secret_key_123")
    result = asyncio.run(verify_bearer_token(creds))
    assert result == "secret_key_123"


def test_auth_invalid_bearer_token(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "FREEAI_API_KEY", "secret_key_123")

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="wrong_key")
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(verify_bearer_token(creds))
    assert exc_info.value.status_code == 401
