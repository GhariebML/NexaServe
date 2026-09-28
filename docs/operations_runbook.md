# NexaServe Operations & Disaster Recovery Runbook

**Version:** 2.0  
**Effective Date:** 2026-09-27  
**Scope:** Day-2 Operations, Secure Maintenance, Backup, and Disaster Recovery Procedures  

---

## 1. Security Protocols for Administrative Operations

### A. Strict Prohibition on Plaintext CLI Secrets
1. **Never pass credentials via command-line arguments:**
   ```bash
   # FORBIDDEN (insecure, stored in shell history and docker inspect):
   docker run -e POSTGRES_PASSWORD=<example-only> ...
   
   # MANDATED (secure environment file or secret injection):
   docker run --env-file /secure/path/.env ...
   ```
2. **Never commit `.env` or backup `.sql` files to git repositories.**
3. **Never print secrets in administrative scripts or CLI logs.**

---

## 2. Secure Database Backup Procedure

To prevent character encoding corruption (e.g. Windows PowerShell UTF-16 BOM injection):
All database dumps must be generated inside the database container and copied out as clean binary streams.

```bash
# 1. Execute pg_dump directly to container filesystem (UTF-8 binary native)
docker exec cs-postgres pg_dump -U postgres customerservice --no-owner --no-acl -f /tmp/backup.sql

# 2. Safely extract backup to persistent backup directory
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
docker cp cs-postgres:/tmp/backup.sql ./backups/backup_${TIMESTAMP}.sql

# 3. Clean up container temporary dump
docker exec cs-postgres rm /tmp/backup.sql

# 4. Verify backup size and header
ls -lh ./backups/backup_${TIMESTAMP}.sql
```

---

## 3. Secure Disaster Recovery Restore Procedure

In the event of cluster failure or migration to fresh infrastructure:

```bash
# 1. Ensure target postgres container is running with ankane/pgvector or pgvector/pgvector
# Do NOT pass passwords directly on the command line; use --env-file:
docker run -d --name cs-postgres-dr --env-file .env -p 5432:5432 ankane/pgvector:latest

# 2. Wait for PostgreSQL initialization
docker exec cs-postgres-dr pg_isready -U postgres

# 3. Copy clean UTF-8 backup into container
docker cp ./backups/clean_backup.sql cs-postgres-dr:/tmp/restore.sql

# 4. Execute restore
docker exec cs-postgres-dr psql -U postgres -d customerservice -f /tmp/restore.sql

# 5. Verify restored schema and row counts
docker exec cs-postgres-dr psql -U postgres -d customerservice -c "SELECT 'knowledge_base' as tbl, count(*) FROM knowledge_base UNION ALL SELECT 'customers', count(*) FROM customers UNION ALL SELECT 'messages', count(*) FROM messages;"

# 6. Verify pgvector extension and embeddings
docker exec cs-postgres-dr psql -U postgres -d customerservice -c "SELECT count(*) FROM knowledge_base WHERE embedding IS NOT NULL;"
```

---

## 4. Routine Maintenance & Credential Rotation

- **n8n Automation API Keys:**
  When generating an API key in n8n UI, set it in the shell environment:
  `export N8N_API_KEY="<new_token>"` or set in `.env`.
  Never hardcode tokens into maintenance scripts.
- **Service Restart after Secret Rotation:**
  ```bash
  docker compose down
  docker compose up -d
  ```
