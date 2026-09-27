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
JWT_EXPIRATION_SECONDS = 3600 * 12  # 12 hours

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

def create_access_token(user_id: str, username: str, role: str, full_name: str, must_change: bool = False) -> str:
    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "full_name": full_name,
        "must_change_password": must_change,
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

def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    user = query_one(
        "SELECT id, username, password_hash, full_name, role, is_active, must_change_password FROM admin_users WHERE username = %s",
        (username,)
    )
    if not user:
        return None
    if not user.get("is_active", True):
        return None
    if not verify_password(password, user["password_hash"]):
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
        "must_change_password": user.get("must_change_password", False)
    }

def update_user_password(user_id: str, new_password: str) -> bool:
    new_hash = hash_password(new_password)
    rows = execute_commit(
        "UPDATE admin_users SET password_hash = %s, must_change_password = FALSE, updated_at = NOW() WHERE id = %s",
        (new_hash, user_id)
    )
    return rows > 0

async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Security(security)) -> Dict[str, Any]:
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided or invalid.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload

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
