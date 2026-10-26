import asyncio
import os
import sys
import time
from pathlib import Path

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

os.environ.setdefault("CS_DB_PASSWORD", "test-only-not-a-real-secret")
os.environ.setdefault("DASHBOARD_JWT_SECRET", "test-only-dashboard-signing-key")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dashboard" / "backend"))

import auth


def _resolve(token):
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token) if token else None
    return asyncio.run(auth.get_current_user(credentials))


def test_raw_signing_secret_is_not_accepted_as_a_bearer_token():
    with pytest.raises(HTTPException) as exc:
        _resolve(auth.JWT_SECRET)
    assert exc.value.status_code == 401


def test_missing_and_forged_tokens_are_rejected():
    for token in (None, "not-a-jwt", jwt.encode({"sub": "x", "role": "admin", "exp": int(time.time()) + 60},
                                                 "some-other-key", algorithm="HS256")):
        with pytest.raises(HTTPException) as exc:
            _resolve(token)
        assert exc.value.status_code == 401


def test_expired_token_is_rejected():
    expired = auth.create_access_token("u1", "agent1", "agent", "Agent One")
    payload = jwt.decode(expired, auth.JWT_SECRET, algorithms=[auth.JWT_ALGORITHM])
    payload["exp"] = int(time.time()) - 5
    with pytest.raises(HTTPException) as exc:
        _resolve(jwt.encode(payload, auth.JWT_SECRET, algorithm=auth.JWT_ALGORITHM))
    assert exc.value.status_code == 401


def test_signed_token_resolves_to_its_own_role():
    token = auth.create_access_token("u1", "agent1", "agent", "Agent One")
    user = _resolve(token)
    assert user["username"] == "agent1"
    assert user["role"] == "agent"
