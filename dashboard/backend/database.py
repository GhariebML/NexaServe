"""
NexaServe Production Admin Dashboard - Core Database Client
Secure connection pool, parameterized query execution, and date/program filtering.
"""
import os
import psycopg2
from psycopg2 import pool
from contextlib import contextmanager
from typing import Generator, Any, List, Dict, Optional, Tuple

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "127.0.0.1")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("CS_DB_NAME", "customerservice")
POSTGRES_USER = os.getenv("CS_DB_USER", "cs_app_user")
POSTGRES_PASSWORD = os.getenv("CS_DB_PASSWORD")
if not POSTGRES_PASSWORD:
    raise RuntimeError("CS_DB_PASSWORD environment variable must be set")

# Fallback to superuser if app user permission is limited
POSTGRES_SUPER_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_SUPER_PASSWORD = os.getenv("POSTGRES_PASSWORD")
if not POSTGRES_SUPER_PASSWORD:
    raise RuntimeError("POSTGRES_PASSWORD environment variable must be set")

db_pool: Optional[pool.SimpleConnectionPool] = None

def init_db_pool():
    global db_pool
    if db_pool is None:
        try:
            db_pool = pool.SimpleConnectionPool(
                minconn=2,
                maxconn=20,
                host=POSTGRES_HOST,
                port=POSTGRES_PORT,
                dbname=POSTGRES_DB,
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD
            )
        except Exception:
            # Fallback to postgres superuser
            db_pool = pool.SimpleConnectionPool(
                minconn=2,
                maxconn=20,
                host=POSTGRES_HOST,
                port=POSTGRES_PORT,
                dbname=POSTGRES_DB,
                user=POSTGRES_SUPER_USER,
                password=POSTGRES_SUPER_PASSWORD
            )

@contextmanager
def get_db() -> Generator[psycopg2.extensions.connection, None, None]:
    if db_pool is None:
        init_db_pool()
    conn = db_pool.getconn()
    try:
        yield conn
    finally:
        db_pool.putconn(conn)

def query_all(sql: str, params: Optional[Tuple[Any, ...]] = None) -> List[Dict[str, Any]]:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            if cur.description is None:
                return []
            cols = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            return [dict(zip(cols, row)) for row in rows]

def query_one(sql: str, params: Optional[Tuple[Any, ...]] = None) -> Optional[Dict[str, Any]]:
    results = query_all(sql, params)
    return results[0] if results else None

def execute_commit(sql: str, params: Optional[Tuple[Any, ...]] = None) -> int:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            conn.commit()
            return cur.rowcount
