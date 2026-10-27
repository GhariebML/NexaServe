"""
NexaServe Production Admin Dashboard - Login Attempt Throttling
Counts failed sign-ins per (username, client IP) in Redis and blocks further
attempts for the rest of the window once the limit is reached.
"""
import hashlib
import logging
import os
from typing import Optional

import redis

MAX_FAILED_ATTEMPTS = int(os.getenv("DASHBOARD_LOGIN_MAX_FAILURES", "5"))
WINDOW_SECONDS = int(os.getenv("DASHBOARD_LOGIN_WINDOW_SECONDS", "900"))

logger = logging.getLogger("nexaserve.auth")
_client: Optional[redis.Redis] = None


def _redis() -> Optional[redis.Redis]:
    global _client
    password = os.getenv("REDIS_PASSWORD")
    if not password:
        return None
    if _client is None:
        _client = redis.Redis(
            host=os.getenv("REDIS_HOST", "127.0.0.1"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=password,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
    return _client


def _key(username: str, client_ip: str) -> str:
    # Hash so raw usernames and IPs are not stored as Redis keys.
    digest = hashlib.sha256(f"{username.strip().lower()}|{client_ip}".encode("utf-8")).hexdigest()
    return f"dashboard:login_failures:{digest}"


def retry_after_seconds(username: str, client_ip: str) -> int:
    """Seconds until another attempt is allowed; 0 when not throttled."""
    client = _redis()
    if client is None:
        return 0
    try:
        key = _key(username, client_ip)
        failures = int(client.get(key) or 0)
        if failures < MAX_FAILED_ATTEMPTS:
            return 0
        return max(int(client.ttl(key)), 1)
    except redis.RedisError:
        # Fail open: a Redis outage must not lock every operator out of the console.
        logger.warning("Login throttle unavailable; attempt allowed without rate limiting")
        return 0


def record_failure(username: str, client_ip: str) -> None:
    client = _redis()
    if client is None:
        return
    try:
        key = _key(username, client_ip)
        with client.pipeline() as pipe:
            pipe.incr(key)
            pipe.expire(key, WINDOW_SECONDS, nx=True)
            pipe.execute()
    except redis.RedisError:
        logger.warning("Login throttle unavailable; failed attempt not recorded")


def clear_failures(username: str, client_ip: str) -> None:
    client = _redis()
    if client is None:
        return
    try:
        client.delete(_key(username, client_ip))
    except redis.RedisError:
        pass
