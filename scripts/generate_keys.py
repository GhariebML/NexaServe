#!/usr/bin/env python3
"""Generate secure random keys for .env and deployment"""
import secrets
import os

# Generate truly random 64-char hex keys
keys = {
    'N8N_ENCRYPTION_KEY': secrets.token_hex(32),
    'N8N_USER_MANAGEMENT_JWT_SECRET': secrets.token_hex(32),
    'DASHBOARD_JWT_SECRET': secrets.token_hex(32),
    'REDIS_PASSWORD': secrets.token_hex(16),
    'CS_DB_PASSWORD': secrets.token_hex(16),
    'N8N_DB_PASSWORD': secrets.token_hex(16),
    'POSTGRES_PASSWORD': secrets.token_hex(16),
}

for k, v in keys.items():
    print(f'{k}={v}')