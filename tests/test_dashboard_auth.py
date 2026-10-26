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
import login_throttle

USER_ID = "11111111-1111-1111-1111-111111111111"


@pytest.fixture
def account(monkeypatch):
    """In-memory admin_users row backing auth's lookups."""
    row = {"username": "agent1", "full_name": "Agent One", "role": "agent", "is_active": True,
           "must_change_password": False, "token_version": 3}

    def query_one(sql, params=None, commit=False):
        if "FROM admin_users WHERE id" in sql:
            return dict(row) if params[0] == USER_ID else None
        raise AssertionError(f"unexpected query: {sql}")

    monkeypatch.setattr(auth, "query_one", query_one)
    return row


def _token(version=3, **overrides):
    claims = {"sub": USER_ID, "username": "agent1", "role": "agent", "full_name": "Agent One",
              "ver": version, "exp": int(time.time()) + 60, "iat": int(time.time())}
    claims.update(overrides)
    return jwt.encode(claims, auth.JWT_SECRET, algorithm=auth.JWT_ALGORITHM)


def _resolve(token, dependency=None):
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token) if token else None
    if dependency is auth.get_authenticated_user:
        return asyncio.run(auth.get_authenticated_user(credentials))
    user = asyncio.run(auth.get_authenticated_user(credentials))
    return asyncio.run(auth.get_current_user(user))


def _status(token, dependency=None):
    with pytest.raises(HTTPException) as exc:
        _resolve(token, dependency)
    return exc.value.status_code, exc.value.detail


def test_raw_signing_secret_is_not_accepted_as_a_bearer_token(account):
    assert _status(auth.JWT_SECRET)[0] == 401


def test_missing_forged_and_expired_tokens_are_rejected(account):
    assert _status(None)[0] == 401
    assert _status("not-a-jwt")[0] == 401
    forged = jwt.encode({"sub": USER_ID, "role": "admin", "ver": 3, "exp": int(time.time()) + 60},
                        "some-other-key", algorithm="HS256")
    assert _status(forged)[0] == 401
    assert _status(_token(exp=int(time.time()) - 5))[0] == 401


def test_signed_token_resolves_with_role_from_the_database(account):
    account["role"] = "supervisor"  # role changed after the token was issued
    user = _resolve(_token())
    assert user["username"] == "agent1"
    assert user["role"] == "supervisor"


def test_bumped_token_version_revokes_older_tokens(account):
    account["token_version"] = 4  # e.g. password changed or user signed out
    assert _status(_token(version=3))[0] == 401
    assert _resolve(_token(version=4))["username"] == "agent1"


def test_deactivated_or_deleted_account_is_rejected(account):
    account["is_active"] = False
    assert _status(_token())[0] == 401
    assert _status(_token(sub="22222222-2222-2222-2222-222222222222"))[0] == 401


def test_pending_password_change_blocks_everything_but_the_change_route(account):
    account["must_change_password"] = True
    # Flag comes from the database, so a token minted before the flag was set is still blocked.
    assert _status(_token(must_change_password=False)) == (403, auth.PASSWORD_CHANGE_REQUIRED)
    assert _resolve(_token(), auth.get_authenticated_user)["must_change_password"] is True


def test_issued_token_carries_the_account_token_version():
    token = auth.issue_token_for({"id": USER_ID, "username": "agent1", "role": "agent",
                                  "full_name": "Agent One", "must_change_password": False, "token_version": 7})
    assert jwt.decode(token, auth.JWT_SECRET, algorithms=[auth.JWT_ALGORITHM])["ver"] == 7


class _FakeRedis:
    def __init__(self):
        self.values, self.ttls = {}, {}

    def get(self, key):
        return self.values.get(key)

    def ttl(self, key):
        return self.ttls.get(key, -1)

    def delete(self, key):
        self.values.pop(key, None)

    def pipeline(self):
        store = self

        class Pipe:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def incr(self, key):
                store.values[key] = int(store.values.get(key, 0)) + 1

            def expire(self, key, seconds, nx=False):
                if not (nx and key in store.ttls):
                    store.ttls[key] = seconds

            def execute(self):
                return []

        return Pipe()


def test_login_throttle_blocks_after_limit_and_resets_on_success(monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setattr(login_throttle, "_redis", lambda: fake)
    for _ in range(login_throttle.MAX_FAILED_ATTEMPTS - 1):
        login_throttle.record_failure("Agent1", "10.0.0.5")
    assert login_throttle.retry_after_seconds("agent1", "10.0.0.5") == 0
    login_throttle.record_failure("agent1", "10.0.0.5")
    assert login_throttle.retry_after_seconds("agent1", "10.0.0.5") == login_throttle.WINDOW_SECONDS
    assert login_throttle.retry_after_seconds("agent1", "10.0.0.6") == 0  # other client unaffected
    login_throttle.clear_failures("agent1", "10.0.0.5")
    assert login_throttle.retry_after_seconds("agent1", "10.0.0.5") == 0


def test_login_throttle_fails_open_when_redis_is_down(monkeypatch):
    class Down:
        def get(self, key):
            raise login_throttle.redis.ConnectionError("down")

    monkeypatch.setattr(login_throttle, "_redis", lambda: Down())
    assert login_throttle.retry_after_seconds("agent1", "10.0.0.5") == 0
