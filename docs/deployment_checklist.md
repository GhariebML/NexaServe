# NexaServe Production Deployment Checklist

**Version:** 2.0  
**Effective Date:** 2026-09-27  
**Scope:** Automated Deployment, Cold-Start Bootstrapping, and Runtime Hardening  

---

## 1. Pre-Deployment Secret & Configuration Validation

- [ ] **No Plaintext Secrets in CLI/Shell History:**
  - Never pass database passwords, encryption keys, or API tokens via `-e KEY=value` or inline CLI arguments.
  - Always use `--env-file .env` or Docker secrets for all container commands.
- [ ] **Environment Configuration Verification:**
  - Copy `.env.example` to `.env`.
  - Populate unique, cryptographically strong passwords for `POSTGRES_PASSWORD`, `N8N_DB_PASSWORD`, `CS_DB_PASSWORD`, `REDIS_PASSWORD`.
  - Generate a 32-character random string for `N8N_ENCRYPTION_KEY`.
  - Generate a secure random string for `N8N_USER_MANAGEMENT_JWT_SECRET`.
  - Confirm that `.env` is listed in `.gitignore` and never committed.
- [ ] **File Permissions:**
  - Restrict `.env` permissions (`chmod 600 .env` or Windows NTFS ACLs to Administrator/Service Account only).

---

## 2. Infrastructure Cold-Start Bootstrapping

Execute bootstrap using docker compose with secure environment injection:

```bash
# 1. Validate docker compose syntax and environment substitution
docker compose config --quiet

# 2. Spin up core infrastructure in background
docker compose up -d

# 3. Monitor container health status without exposing credentials
docker compose ps
```

Verify that all 5 core containers achieve `(healthy)` status:
- `cs-postgres` (PostgreSQL 16 + pgvector)
- `cs-whatsapp` (Baileys WhatsApp Gateway)
- `cs-ollama` (Ollama local inference engine)
- `cs-n8n` (Workflow orchestration engine)
- `cs-redis` (Session cache & queue manager)

---

## 3. Post-Bootstrap Verification

- [ ] **Database Initialization Check:**
  ```bash
  docker compose exec postgres psql -U postgres -c "SELECT datname FROM pg_database WHERE datname IN ('n8n', 'customerservice');"
  ```
- [ ] **Schema & Extensions Check:**
  ```bash
  docker compose exec postgres psql -U postgres -d customerservice -c "SELECT extname FROM pg_extension WHERE extname IN ('vector', 'uuid-ossp', 'pg_trgm');"
  ```
- [ ] **n8n Webhook Health Check:**
  ```bash
  curl -fsSL -X POST http://localhost:5678/webhook/customer-service -H "Content-Type: application/json" -d '{"channel":"healthcheck","customer_message":"ping"}'
  ```

---

## 4. Post-Deployment Security Sign-off

- [ ] Ensure all local test tokens in `scripts/` have been rotated and cleared.
- [ ] Ensure no logs in `/tmp` or `.system_generated` contain raw credentials.
- [ ] Confirm `backups/*.sql` are restricted to authorized storage.
