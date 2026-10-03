# FINAL RELEASE BASELINE — NexaServe Ministry Deployment

**Generated:** 2026-09-27T22:05:00Z
**Status:** DRAFT — undergoing final freeze

---

## Release Identity

| Field | Value |
|-------|-------|
| Release Version | 0.1.0 (deployment candidate) |
| Git Commit | `b056198` (HEAD of master) |
| Previous Commit | `72f6e68` (deployment bundle was built from this — OUT OF DATE) |
| Date/Time | 2026-09-27T22:05:00Z |
| Repository | https://github.com/GhariebML/NexaServe |
| Target | Ubuntu 24.04 x86_64, Docker Compose, NVIDIA GPU (if available) |

---

## Service Versions

| Service | Version | Image | Container |
|---------|---------|-------|-----------|
| PostgreSQL | 16.15 | pgvector/pgvector:pg16 | cs-postgres |
| pgvector | 0.8.6 | (extension) | cs-postgres |
| Redis | 7.4.11 | redis:7-bookworm | cs-redis |
| n8n | 2.38.1 | docker.n8n.io/n8nio/n8n:latest | cs-n8n |
| Ollama | latest | ollama/ollama:latest | cs-ollama |
| WhatsApp Bridge | custom | nexaserve-whatsapp (built from infra/whatsapp/) | cs-whatsapp |
| Dashboard | custom | nexaserve-dashboard (built from dashboard/) | cs-dashboard |

---

## Models

| Model | Size | Type | Status |
|-------|------|------|--------|
| qwen2.5:3b | 1.9 GB | Chat (generate) | Loaded, 100% CPU |
| qwen2.5:1.5b | 986 MB | Chat (generate) | Available, not loaded |
| qwen2.5:7b | 4.7 GB | Chat (generate) | Available, CANNOT LOAD (exceeds Docker VM memory) |
| nomic-embed-text | 274 MB | Embeddings (768-dim) | Loaded, 100% CPU |

**Embedding dimension:** 768
**Chat model in use:** qwen2.5:3b

---

## Database

| Field | Value |
|-------|-------|
| PostgreSQL | 16.15 |
| Extensions | pg_trgm 1.6, plpgsql 1.0, uuid-ossp 1.1, vector 0.8.6 |
| customerservice tables | 19 |
| knowledge_base rows | 73 (DEBI: 45, DIGILIANS: 26, COMMON: 2) |
| Embedding coverage | 100% (73/73) |
| Vector dimension | 768 |
| customers | 89 (73% synthetic test data) |
| tickets | 92 |
| conversations | 91 |
| messages | 2119 |
| admin_users | 3 (admin, agent, readonly) |
| Migration ledger | **MISSING** for customerservice DB |

---

## n8n Workflows

| Status | Count |
|--------|-------|
| Total in live DB | 38 |
| Active | 16 |
| Inactive | 22 |
| Canonical production set | 10 (00-06, 04A-04D) |
| Duplicate names in live | 5 workflows have 4-5 versions each |

---

## Current Environment Limitations (DEVELOPMENT HOST)

| Issue | Detail |
|-------|--------|
| GPU | **NOT AVAILABLE** — AMD Radeon integrated, no NVIDIA |
| Host memory | 15.28 GB total, 93.1% used, Docker VM capped at 3.49 GB |
| Disk C: | 1.4 GB free (CRITICAL) |
| Disk G: | 1.4 GB free (CRITICAL) |
| Disk E: | 19.5 GB free (87%) |
| Ollama CPU | 100% on all inference |

---

## Known Limitations

1. **No GPU** — All inference is CPU-bound. qwen2.5:7b cannot load (4.7 GB > 3.49 GB Docker VM limit).
2. **Deployment bundle v0.1.0 is stale** — built from commit `72f6e68`, current is `b056198`.
3. **73% synthetic test data** in customers table — not production data.
4. **No migration ledger** for customerservice DB — cannot verify migration state.
5. **n8n encryption key** appears patterned/sequential — needs rotation.
6. **host.docker.internal references** in 3 workflows — won't resolve in containerized n8n.
7. **Duplicate workflows** in live n8n — 5 names have 4-5 versions each.
8. **No WhatsApp E2E test** performed.
9. **No backup/restore test** performed.
10. **No Ministry network validation** performed.

---

## Validation Evidence

| Check | Status |
|-------|--------|
| Docker containers healthy | PASS (6/6) |
| PostgreSQL connectivity | PASS |
| Redis connectivity | PASS |
| Ollama running | PASS |
| n8n healthz | PASS |
| WhatsApp CONNECTED | PASS |
| Dashboard ready | PASS |
| pgvector extension | PASS |
| Vector dimension 768 | PASS |
| KB embedding coverage 100% | PASS |
| Secret scan | PASS (after fixes) |
| GPU inference | FAIL (no GPU) |
| Backup/restore | NOT TESTED |
| WhatsApp E2E | NOT TESTED |
| Ministry network | NOT TESTED |