"""
NexaServe Production Admin Dashboard - Main Server Application
Mounts API routers, Static file hosting for frontend, CORS, and Lifespan lifecycle.
"""
import os
import sys
from fastapi import FastAPI, HTTPException, status, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from database import init_db_pool, query_one, ReportQueryTimeoutError
import auth
import login_throttle
from routes import router as dashboard_router

app = FastAPI(
    title="NexaServe Production Admin Dashboard",
    description="Real-time operational dashboard connected to NexaServe PostgreSQL database.",
    version="2.0.0"
)


@app.exception_handler(ReportQueryTimeoutError)
async def report_query_timeout_handler(_request: Request, _exc: ReportQueryTimeoutError):
    return JSONResponse(status_code=504, content={
        "detail": "Report generation exceeded the database time limit; retry with narrower filters"
    })

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv("DASHBOARD_CORS_ORIGINS", "").split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    init_db_pool()

@app.get("/health/live")
async def health_live():
    return {"status": "ok"}

@app.get("/health/ready")
async def health_ready():
    try:
        query_one("SELECT 1 AS ok")
        redis_pw = os.getenv("REDIS_PASSWORD")
        if not redis_pw:
            raise RuntimeError("Redis health check is not configured")
        import redis
        client = redis.Redis(
            host=os.getenv("REDIS_HOST", "127.0.0.1"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=redis_pw,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        client.ping()
        return {"status": "ready"}
    except Exception:
        raise HTTPException(status_code=503, detail="Dashboard dependencies are not ready")

class LoginRequest(BaseModel):
    username: str
    password: str

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _throttle_or_raise(username: str, client_ip: str) -> None:
    wait = login_throttle.retry_after_seconds(username, client_ip)
    if wait:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed attempts; try again later",
            headers={"Retry-After": str(wait)},
        )


def _public_user(user: dict) -> dict:
    return {key: user[key] for key in ("id", "username", "full_name", "role", "must_change_password")}


# Sync handlers: Argon2 verification and DB access block, so FastAPI runs these in its threadpool.
@app.post("/api/auth/login")
def login(req: LoginRequest, request: Request):
    client_ip = _client_ip(request)
    _throttle_or_raise(req.username, client_ip)
    user = auth.authenticate_user(req.username, req.password)
    if not user:
        login_throttle.record_failure(req.username, client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    login_throttle.clear_failures(req.username, client_ip)
    return {
        "access_token": auth.issue_token_for(user),
        "token_type": "bearer",
        "user": _public_user(user)
    }

@app.post("/api/auth/change-password")
def change_password(req: ChangePasswordRequest, request: Request,
                    current_user: dict = Depends(auth.get_authenticated_user)):
    client_ip = _client_ip(request)
    _throttle_or_raise(current_user["username"], client_ip)
    user = auth.authenticate_user(current_user["username"], req.old_password)
    if not user:
        login_throttle.record_failure(current_user["username"], client_ip)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password verification failed"
        )
    if len(req.new_password) < auth.MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"New password must be at least {auth.MIN_PASSWORD_LENGTH} characters long"
        )
    if req.new_password == req.old_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="New password must differ from the current password")
    new_version = auth.update_user_password(current_user["sub"], req.new_password)
    if new_version is None:
        raise HTTPException(status_code=500, detail="Failed to update password")
    login_throttle.clear_failures(current_user["username"], client_ip)
    # Every earlier token (including the one used for this call) is now revoked; hand back a fresh one.
    refreshed = {**user, "must_change_password": False, "token_version": new_version}
    return {
        "message": "Password updated successfully",
        "access_token": auth.issue_token_for(refreshed),
        "token_type": "bearer",
        "user": _public_user(refreshed),
    }

@app.post("/api/auth/logout")
def logout(current_user: dict = Depends(auth.get_authenticated_user)):
    """Revokes all of this user's sessions (tokens are stateless, so revocation is per user)."""
    auth.revoke_user_tokens(current_user["sub"])
    return {"message": "Signed out"}

# Mount dashboard API
app.include_router(dashboard_router)

# Mount static frontend
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/")
async def serve_index():
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "NexaServe Admin Dashboard API Running. Frontend building..."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8090, reload=False)
