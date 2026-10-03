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

POOL_MAX_CONNECTIONS = max(2, int(os.getenv("DASHBOARD_DB_POOL_MAX", "8")))

db_pool: Optional[pool.ThreadedConnectionPool] = None

def init_db_pool():
    global db_pool
    if db_pool is None:
        try:
            db_pool = pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=POOL_MAX_CONNECTIONS,
                host=POSTGRES_HOST,
                port=POSTGRES_PORT,
                dbname=POSTGRES_DB,
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD
            )
        except Exception as exc:
            raise RuntimeError("Dashboard database connection failed for configured application user") from exc

@contextmanager
def get_db() -> Generator[psycopg2.extensions.connection, None, None]:
    if db_pool is None:
        init_db_pool()
    conn = db_pool.getconn()
    try:
        yield conn
    finally:
        close_connection = bool(conn.closed)
        if not close_connection:
            try:
                conn.rollback()
            except psycopg2.Error:
                close_connection = True
        db_pool.putconn(conn, close=close_connection)

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
