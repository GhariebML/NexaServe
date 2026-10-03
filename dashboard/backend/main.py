"""
NexaServe Production Admin Dashboard - Main Server Application
Mounts API routers, Static file hosting for frontend, CORS, and Lifespan lifecycle.
"""
import os
import sys
from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from database import init_db_pool, query_one
import auth
from routes import router as dashboard_router

app = FastAPI(
    title="NexaServe Production Admin Dashboard",
    description="Real-time operational dashboard connected to NexaServe PostgreSQL database.",
    version="2.0.0"
)

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

@app.post("/api/auth/login")
async def login(req: LoginRequest):
    user = auth.authenticate_user(req.username, req.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    token = auth.create_access_token(
        user_id=user["id"],
        username=user["username"],
        role=user["role"],
        full_name=user["full_name"],
        must_change=user.get("must_change_password", False)
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user
    }

@app.post("/api/auth/change-password")
async def change_password(req: ChangePasswordRequest, current_user: dict = Depends(auth.get_current_user)):
    user = auth.authenticate_user(current_user["username"], req.old_password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password verification failed"
        )
    if len(req.new_password) < 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 12 characters long"
        )
    success = auth.update_user_password(current_user["sub"], req.new_password)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update password")
    return {"message": "Password updated successfully"}

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
