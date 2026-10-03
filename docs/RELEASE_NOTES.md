# RELEASE NOTES — NexaServe 0.1.0

**Release Date:** 2026-09-27
**Git Commit:** b056198
**Branch:** master
**Type:** Deployment Candidate

---

## Changes Since Previous Release (72f6e68)

### Security
- Removed all hardcoded secrets from `dashboard/backend/database.py`, `dashboard/backend/routes.py`, `tests/test_dashboard_production.py`, `tests/test_security.py`
- Deleted `.opencode/temp_query.js` (contained exposed DB password)
- Added `scripts/secret_scan.py` for CI secret scanning
- All passwords now require environment variables; `RuntimeError` raised if unset

### Infrastructure
- Added `OLLAMA_URL` environment variable to `docker-compose.yml` whatsapp service
- Fixed `host.docker.internal` references in 3 n8n workflows → `cs-ollama:11434`
- Added `OLLAMA_URL` to docker-compose.yml

### RAG / Knowledge Base
- Fixed `isBenefits` and `isTracks` undefined variable errors in SubWF 04B (`Program Detector & Query Normalizer` node)
- Fixed duplicate `topicCategory` declaration in `Format RAG Knowledge Response` node
- Added 9 new DEPI FAQ entries (admission appeal, exam incident, training feedback, platform bug, etc.)
- Updated keywords in PostgreSQL `knowledge_base` table for all new entries

### Dashboard
- Added `admin_users` table with Argon2id password hashing
- Implemented JWT-based authentication with role isolation (admin/agent/readonly)
- Added health endpoint and KPI dashboards

### Deployment
- Re-synced `deployment/` bundle with current codebase
- Updated `inventory.json` with current workflow set
- Updated `VERSION` to 0.1.0

### Documentation
- Added `docs/FINAL_RELEASE_BASELINE.md`
- Added `docs/FINAL_BLOCKERS.md`
- Added `docs/RELEASE_NOTES.md`
- Added `docs/RELEASE_MANIFEST.md`
- Updated `docs/NEXASERVE_FINAL_PRODUCTION_READINESS_REPORT.md`

---

## Known Issues

See `docs/FINAL_BLOCKERS.md` for complete classification.

**P0 (blocking):**
- No GPU on development host
- Deployment bundle was stale (now fixed)
- No backup/restore test

**P1 (blocking):**
- n8n encryption key needs rotation
- host.docker.internal references in live n8n (fixed in files, needs re-import)
- Duplicate workflows in live n8n
- 73% synthetic test data in customers table
- No migration ledger for customerservice DB
- WhatsApp E2E not verified

---

## Deployment Instructions

See `deployment/DEPLOYMENT.md` for full runbook.

**First command:**
```bash
cd /opt/nexaserve && sudo bash deployment/scripts/00_preflight.sh
```

**Quick start (connected Ubuntu 24.04 with Docker + NVIDIA):**
```bash
cd /opt/nexaserve
sudo bash deployment/scripts/01_install_host_dependencies.sh
sudo bash deployment/scripts/02_install_docker.sh
sudo bash deployment/scripts/03_install_nvidia_toolkit.sh
sudo bash deployment/scripts/deploy.sh gpu
```