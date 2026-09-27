"""
Database configuration and connection utility for NexaServe scripts.
Safely loads credentials from environment variables or root .env file.
Never hardcodes passwords or sensitive secrets.
"""

import os
import psycopg2
from pgvector.psycopg2 import register_vector

def load_env_file():
    """Parse .env file from project root into os.environ if not already set."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(base_dir, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip("\"'")
                    if k not in os.environ:
                        os.environ[k] = v

load_env_file()

DB_NAME = os.getenv("CS_DB_NAME", "customerservice")
DB_USER = os.getenv("CS_DB_USER", "cs_app_user")
DB_PASS = os.getenv("CS_DB_PASSWORD")
DB_HOST = os.getenv("POSTGRES_HOST", "127.0.0.1")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")

OLLAMA_EMBED_URL = os.getenv("OLLAMA_EMBED_URL", "http://127.0.0.1:11434/api/embed")
OLLAMA_GENERATE_URL = os.getenv("OLLAMA_GENERATE_URL", "http://localhost:11434/api/generate")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
EMBED_DIMENSION = int(os.getenv("EMBED_DIMENSION", "768"))
LLM_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")

def get_db_connection():
    """Return an active PostgreSQL connection with pgvector registered."""
    if not DB_PASS:
        raise ValueError("Database password not configured. Please set CS_DB_PASSWORD in environment or .env file.")
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=DB_PORT
    )
    register_vector(conn)
    return conn

ADMIN_DB_USER = os.getenv("POSTGRES_USER", "postgres")
ADMIN_DB_PASS = os.getenv("POSTGRES_PASSWORD")

def get_admin_db_connection(dbname=None):
    """Return an admin/superuser connection for running DDL and maintenance."""
    if not ADMIN_DB_PASS:
        raise ValueError("Admin password not configured. Please set POSTGRES_PASSWORD in environment or .env file.")
    conn = psycopg2.connect(
        dbname=dbname or DB_NAME,
        user=ADMIN_DB_USER,
        password=ADMIN_DB_PASS,
        host=DB_HOST,
        port=DB_PORT
    )
    register_vector(conn)
    return conn
