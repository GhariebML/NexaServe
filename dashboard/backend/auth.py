"""
NexaServe Production Admin Dashboard - Authentication & RBAC Layer
Argon2id Password Hashing, JWT Bearer Tokens, and Role-Based Authorization.
"""
import os
import time
import secrets
import argon2
import jwt
from typing import Optional, Dict, Any
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from database import query_one, execute_commit

JWT_SECRET = os.getenv("DASHBOARD_JWT_SECRET")
if not JWT_SECRET:
    raise RuntimeError(
        "DASHBOARD_JWT_SECRET environment variable is not set. "
        "Generate one with: python3 -c 'import secrets; print(secrets.token_hex(32))'"
    )
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_SECONDS = int(os.getenv("DASHBOARD_JWT_TTL_SECONDS", str(3600 * 8)))  # one shift
PASSWORD_CHANGE_REQUIRED = "password_change_required"
MIN_PASSWORD_LENGTH = 12

security = HTTPBearer(auto_error=False)

# Enterprise Argon2id Password Hasher (OWASP recommended parameters)
ph = argon2.PasswordHasher(
    time_cost=2,
    memory_cost=65536,  # 64 MB
    parallelism=1,
    hash_len=32,
    type=argon2.Type.ID
)

def hash_password(password: str) -> str:
    """Hashes password using Argon2id with memory-hard work factors."""
    return ph.hash(password)

def verify_password(plain_password: str, stored_hash: str) -> bool:
    """Verifies plaintext against Argon2id hash with timing attack resistance."""
    try:
        return ph.verify(stored_hash, plain_password)
    except Exception:
        return False

def create_access_token(user_id: str, username: str, role: str, full_name: str, must_change: bool = False,
                        token_version: int = 0) -> str:
    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "full_name": full_name,
        "must_change_password": must_change,
        "ver": token_version,
        "exp": int(time.time()) + JWT_EXPIRATION_SECONDS,
        "iat": int(time.time()),
        "iss": "NexaServe-Auth-Engine"
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except (jwt.PyJWTError, Exception):
        return None

# Verifying against a throwaway hash for unknown users keeps response time from revealing valid usernames.
_DUMMY_HASH = ph.hash(secrets.token_hex(16))

def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    user = query_one(
        "SELECT id, username, password_hash, full_name, role, is_active, must_change_password, token_version "
        "FROM admin_users WHERE username = %s",
        (username,)
    )
    if not user:
        verify_password(password, _DUMMY_HASH)
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    if not user.get("is_active", True):
        return None
    
    # Update last login
    try:
        execute_commit("UPDATE admin_users SET last_login_at = NOW() WHERE id = %s", (user["id"],))
    except Exception:
        pass
        
    return {
        "id": str(user["id"]),
        "username": user["username"],
        "full_name": user["full_name"],
        "role": user["role"],
        "must_change_password": bool(user.get("must_change_password", False)),
        "token_version": int(user.get("token_version") or 0),
    }

def issue_token_for(user: Dict[str, Any]) -> str:
    return create_access_token(
        user_id=user["id"], username=user["username"], role=user["role"], full_name=user["full_name"],
        must_change=user.get("must_change_password", False), token_version=user.get("token_version", 0),
    )

def update_user_password(user_id: str, new_password: str) -> Optional[int]:
    """Set a new password and revoke every token issued before it; returns the new token version."""
    new_hash = hash_password(new_password)
    row = query_one(
        "UPDATE admin_users SET password_hash = %s, must_change_password = FALSE, "
        "token_version = token_version + 1, updated_at = NOW() WHERE id = %s RETURNING token_version",
        (new_hash, user_id),
        commit=True,
    )
    return int(row["token_version"]) if row else None

def revoke_user_tokens(user_id: str) -> None:
    execute_commit("UPDATE admin_users SET token_version = token_version + 1 WHERE id = %s", (user_id,))

def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail,
                         headers={"WWW-Authenticate": "Bearer"})

async def get_authenticated_user(credentials: Optional[HTTPAuthorizationCredentials] = Security(security)) -> Dict[str, Any]:
    """Valid session regardless of the forced-password-change flag (used by the change-password route)."""
    if not credentials or not credentials.credentials:
        raise _unauthorized("Authentication credentials were not provided or invalid.")
    # Only signed, unexpired JWTs are accepted; service-to-service routes use
    # their own scoped tokens (e.g. WHATSAPP_INGEST_TOKEN) instead of admin access.
    payload = decode_access_token(credentials.credentials)
    if not payload or not payload.get("sub"):
        raise _unauthorized("Invalid or expired authentication token.")
    # The database is the source of truth, so deactivation, role changes, logout and
    # password changes take effect on the next request instead of at token expiry.
    try:
        account = query_one(
            "SELECT username, full_name, role, is_active, must_change_password, token_version "
            "FROM admin_users WHERE id = %s::uuid",
            (payload["sub"],),
        )
    except Exception:
        account = None
    if not account or not account.get("is_active", True) \
            or int(account.get("token_version") or 0) != int(payload.get("ver", 0)):
        raise _unauthorized("Session is no longer valid; please sign in again.")
    return {
        **payload,
        "username": account["username"],
        "full_name": account["full_name"],
        "role": account["role"],
        "must_change_password": bool(account.get("must_change_password")),
    }

async def get_current_user(user: Dict[str, Any] = Security(get_authenticated_user)) -> Dict[str, Any]:
    """Valid session that is allowed to use the dashboard (no pending forced password change)."""
    if user.get("must_change_password"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=PASSWORD_CHANGE_REQUIRED)
    return user

def require_role(*allowed_roles: str):
    async def role_checker(current_user: Dict[str, Any] = Security(get_current_user)):
        user_role = current_user.get("role", "readonly")
        if "admin" not in allowed_roles and user_role == "admin":
            return current_user  # admin has superuser privileges
        if user_role not in allowed_roles and user_role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Operation requires one of roles: {', '.join(allowed_roles)}. Current role: {user_role}"
            )
        return current_user
    return role_checker
