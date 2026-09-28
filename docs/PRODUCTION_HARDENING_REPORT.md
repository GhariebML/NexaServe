# NexaServe Production Hardening & Deployment Reconciliation Report

**Date:** 2026-09-28 (Africa/Cairo)
**Target:** Ministry server, Ubuntu 24.04.5 LTS, NVIDIA RTX 2000 Ada 16 GiB, driver 580.178.04
**Deployment path:** `/opt/nexaserve/deployment` · data root `/var/lib/nexaserve`
**Canonical repository:** `https://github.com/GhariebML/NexaServe.git`, branch `master`
**Bundle version:** 0.1.0 → **0.1.1**
**Scope:** reconcile the source tree with the working server, fix root causes in source, rotate exposed credentials, re-verify. No WhatsApp pairing, FQDN/TLS, firewall or public exposure was performed.

> This report contains no secret values. Secret-related findings are described, never reproduced.

---

## 1. Initial server state

| Item | State before this pass |
|---|---|
| Repository | `master` @ `b056198`, clean working tree, shallow clone |
| Compose project | `nexaserve`, 6 services, network `nexaserve-backend` |
| Containers | postgres, redis, ollama, n8n, whatsapp, dashboard: all `healthy`, 0 restarts |
| Volumes | `nexaserve_{postgres,redis,ollama,n8n,whatsapp-auth,source}-data`/`-auth` (6), all preserved |
| Images | pinned by digest: `pgvector/pgvector:pg16`, `redis:7-bookworm`, `ollama/ollama`, `n8n:2.38.1`; locally built `nexaserve-{whatsapp,dashboard,scraper,kb-ingest}` |
| Workflows | 10 imported and active; 20 Postgres nodes bound to one credential |
| Knowledge base | 36 active rows (official DEPI scrape) |
| Server-only patches | 4 hand edits in `/opt/nexaserve/deployment` (see §2) |

**Defect found in the baseline:** the Ollama container was running **on CPU** (`DeviceRequests=null`, `ollama ps` → `100% CPU`). The runbook treats silent CPU fallback as a hard failure (Gate 1). See Bug 8. GPU placement was restored first by recreating only the `ollama` service with the GPU overlay; the model volume was preserved and both models remained present.

A non-secret snapshot (service config hashes, `compose config --no-interpolate`, image digests, volumes, networks, container start/restart data, workflow list) was saved to `/var/lib/nexaserve/diagnostics/hardening-snapshot-20260928T102649Z/` (mode 0700).

## 2. Source / deployment reconciliation

| File | Canonical repo (`b056198`) | Server (before) | Intended fix | Status |
|---|---|---|---|---|
| `compose/docker-compose.yml` | `../assets`, `../application`, `../migrations`, `../config` | hand-edited to `./…` | `./…` in source (see Bug 1) | Fixed in source; server content identical |
| `scripts/set_permissions.sh` | chmod 0750 on `assets/postgres/*.sh` | init script hand-set to 0755 | keep mounted assets world-readable (Bug 2) | Fixed |
| `scripts/13_initialize_models.sh` | tests `127.0.0.1:11434` (host) | unchanged; generation tested by hand inside container | test the Compose service (Bug 3) | Rewritten |
| `application/ingestion/Dockerfile` | `COPY db_config.py` from context root | duplicate `application/ingestion/db_config.py` copied by hand | build from `scripts/` (Bug 4) | Fixed; duplicate removed from server |
| `application/scraper/requirements.runtime.txt` | no `playwright` | `playwright==1.63.0` appended | pin in source (Bug 5) | Fixed; server content identical |
| `application/{scraper,ingestion}/…/data/final/` | gitignored, absent | empty placeholder dirs created by hand | not a build input (Bug 6) | Fixed; placeholders removed from server |
| `scripts/common.sh` | `dc()` without GPU overlay | unchanged (caused Bug 8) | always apply GPU overlay | Fixed |
| `assets/n8n/workflows/*.json` | no `errorWorkflow` | live n8n had it set via API | set in exports (Bug 9) | Fixed |
| `MANIFEST.sha256` | not shipped | generated on server | ship generated manifest (Bug 7) | Fixed |

## 3–5. Bugs, root causes and source-level fixes

| # | Bug | Root cause | Source fix |
|---|---|---|---|
| 1 | Compose bind mounts/build contexts resolved **outside** the bundle (`/opt/nexaserve/assets/…`); Docker would create empty directories | Paths were written relative to `compose/`, but every script and runbook command passes `--project-directory <deployment>`, against which Compose resolves relative paths | Paths changed to `./…`. A clean clone resolves 0 paths outside the deployment folder |
| 2 | First Postgres boot skipped DB/role/schema creation (`init-databases.sh: Permission denied`), leaving `customerservice` missing | `set_permissions.sh` made the init script 0750 `depi:depi`; the container's `postgres` user (uid 999) is "other" and could not read it. Git's default 0644 would have worked (the entrypoint sources non-executable scripts) | Operator scripts 0750; container-mounted `assets/ migrations/ config/` dirs 0755, files 0644, Postgres init scripts 0755; `.env` 0600. Never group/world-writable. All `.sh` tracked `100755` in Git |
| 3 | Model test could pass or fail against the **host** Ollama | Hard-coded `curl http://127.0.0.1:11434`; the container publishes no host port, and the server has an unrelated native Ollama on that address | Requests go from the n8n container to `http://ollama:11434` (the path workflows use). Validates non-empty generation, embedding dimension = `EMBED_DIMENSION`, GPU reservation and `100% GPU` placement. Pulls only missing models (offline-safe). Non-zero exit on any failure. `MODEL_CHAT`/`MODEL_EMBED`/`EXPECT_DIM` overrides allow failure testing |
| 4 | Ingestion image build failed: `"/db_config.py": not found` | Dockerfile copied `db_config.py` from the context root; the canonical file lives in `scripts/`, which is already copied | Removed the redundant `COPY`; image uses `/app/scripts/db_config.py` |
| 5 | Scraper container failed: `No module named 'playwright'` | `mcr.microsoft.com/playwright/python:v1.63.0-noble` ships browsers but not the Python package; runtime requirements omitted it | `playwright==1.63.0` pinned to match the base image's browser build |
| 6 | Both tool images required gitignored `data/final/` at build time | Scraper output (runtime data, `data/` is gitignored) was treated as a build input, though both services mount the `source-data` volume over it at runtime | Removed the `COPY data/final/` lines; directories are created in the image and populated only in the volume via `scripts/refresh_sources.sh`. `.dockerignore` excludes `.env`, caches and `data` |
| 7 | Bundle shipped without `MANIFEST.sha256`; the generator would fingerprint any file present | Manifest was expected to be generated at transfer time | `generate_checksums.sh` refuses to run if secret artifacts are present (`*.dump`, `*.secret`, `*.pem`, `*.key`, credentials, auth state) and skips caches/logs; manifest shipped (132 files) |
| 8 | **Silent CPU fallback:** running `kb-ingest` recreated Ollama without GPU; healthcheck still passed | `common.sh` `dc()` used only the base Compose file; `compose run` of a tools service reconciles dependencies and recreated `ollama` without the GPU overlay's device reservation | `dc()` always applies `docker-compose.gpu.yml` (`NEXASERVE_OFFLINE=1` adds the offline overlay); `deploy.sh`/`install_offline.sh` use `dc`; `healthcheck.sh` fails when Ollama lacks a GPU reservation |
| 9 | Global Error Handler never triggered | Exported workflows had no `settings.errorWorkflow` | 9 workflows reference `CSWF000000000008` (surgical JSON edit, formatting preserved) |
| 10 | Clean `kb-ingest` build failed intermittently (`python-dateutil … from versions: none`) | Environmental: one PyPI CDN edge reachable from the target network stalls index pages beyond pip's 15 s × 5 retries | Tool images use `pip --timeout 60 --retries 10`. The network path should still be reviewed (§13) |

Also hardened: `backup.sh` sets `umask 077` (dumps were 0664 inside a 0700 directory). A generic example password literal in `docs/operations_runbook.md` (not a live credential) was replaced with a placeholder.

## 6. Verification performed

- `bash -n` on every tracked shell script; `git diff --check` clean; no CRLF.
- `docker compose config --quiet` passes; resolved paths all inside the deployment folder.
- Postgres init path tested from a **clean clone** after `set_permissions.sh` under `umask 077`, in a throwaway container (`--network none`, anonymous volume, removed afterwards): script executed; `n8n` and `customerservice` created; `vector`, `pg_trgm`, `uuid-ossp` present; migration ledger = 3. Production volume untouched.
- `13_initialize_models.sh` against production: generation OK, 768-d embedding, `qwen2.5:3b 100% GPU`, exit 0. Failure paths: wrong expected dimension → exit 1; nonexistent model → exit 1. Host Ollama serves only `qwen3-vl:8b`, so a pass cannot come from it.

## 7. Security remediation

| Item | Action | Result |
|---|---|---|
| n8n public-API key exposed in conversation context | Revoked by deleting its row from n8n's `user_api_keys` table; local copy shredded. No replacement created (audits use the n8n CLI/DB) | Old key → HTTP 401; 0 API keys exist |
| Dashboard bootstrap admin password written to a home-directory file | Logged in with it, changed via `POST /api/auth/change-password` to a new random value stored only in `/var/lib/nexaserve/secrets/dashboard_admin.secret` (dir 0700, file 0600); bootstrap file shredded | Old password → 401; new login OK, `must_change_password=false`, protected API 200 |
| Secret audit (§7a) | See below | No active secret in source control |

### 7a. Secret audit

| Location | Finding | Action |
|---|---|---|
| Git-tracked files (all, excluding `node_modules`) | No JWT-shaped tokens, private keys or provider keys. Password/secret pattern hits reviewed with masking: all are variable references (`os.getenv`, function arguments, test fixtures) plus one generic docs example | Docs example replaced with a placeholder |
| Git history | Not audited: the working clone is shallow (1 commit) | Run a full-history secret scan (e.g. gitleaks) on a full clone before publishing; do not rewrite history without approval |
| Live `.env` values (7 secrets) | No copy outside `.env` in the repo, deployment folder, diagnostics, `/tmp`, shell history or user config | None |
| Built images (4 app/tool images) | No `.env`, credential or key files (only public CA bundles) | None |
| Backups `/var/lib/nexaserve/backups/*` | `env.secret` and DB dumps are secret-bearing by design (dir 0700) | Move off-host to encrypted storage (§13) |
| `/var/lib/nexaserve/secrets/dashboard_admin.secret` | Current dashboard admin password | Operator: move into the Ministry vault, then delete the file |
| Operator workstation | Server SSH password was supplied in chat and is weak | Rotate the SSH password; prefer key-only SSH (§13) |

## 8. n8n workflow credential audit (active versions)

| Check | Result |
|---|---|
| Credentials | 1: `Postgres account` (postgres), database `customerservice`, user `cs_app_user` |
| Postgres nodes bound | **20/20**: 02 (2), 04A (1), 04B (1), 04C (3), 04D (7), 05 (3), 06 (1), Error Handler (1) |
| Hardcoded passwords in workflow JSON | none (pattern scan and live-DB-password comparison) |
| Sub-workflow references (Master 01) | 02, 03, 04A, 04B, 04C, 05, 06: all resolve to existing active workflows |
| Webhook paths | `customer-service` (Master 01), `agent-response` (04D) |
| Ollama endpoints | `http://cs-ollama:11434/api/{generate,embed}` (internal) |
| WhatsApp endpoint | `$env.WHATSAPP_BRIDGE_URL` or `http://cs-whatsapp:8080` (internal) |
| Error workflow | 9 workflows → `CSWF000000000008`; handler = Error Trigger → `INSERT INTO audit_logs`; insert validated as `cs_app_user` in a rolled-back transaction |
| Activation | all 10 active, each with a published active version |

## 9. Clean-build result

Fresh `git clone` of the committed tree into a temporary workspace (`umask 077`), throwaway `.env`, separate Compose project name (production tags untouched):

| Image | Result |
|---|---|
| `postgres`, `redis`, `ollama`, `n8n` | pinned digests pulled/validated |
| `whatsapp` | built `--no-cache` |
| `dashboard` | built `--no-cache` |
| `scraper` | built `--no-cache`; `playwright 1.63.0`, Chromium launches headless; extraction modules import; 7 official targets |
| `kb-ingest` | built `--no-cache`; `db_config`/`ingest_knowledge`/pandas/PyMuPDF/pgvector import; no DB credential in image (connect without env → `ValueError`); empty `data/final` |

No untracked or server-only file was needed. The workspace and clean-build images were removed afterwards.

## 10. Runtime regression (after reconciliation)

Server reconciliation: deployment folder and databases backed up (`/var/lib/nexaserve/backups/deployment-pre-0.1.1-20260928T105203Z.tar.gz`, `…/20260928T105203Z/`); bundle synced from the commit with `.env` preserved; server-only workarounds removed; manifest and `verify_bundle.sh` pass. **Service config hashes were identical before and after**, and `up --dry-run` recreated nothing, so no running container was restarted. Only the `kb-ingest` and `scraper` tool images were rebuilt.

| Check | Result |
|---|---|
| `healthcheck.sh` (now includes GPU reservation) | PASS, 6/6 healthy |
| `smoke.sh` | PASS: pgvector/pg_trgm/uuid-ossp; 36/36 embedded; ledger 3 |
| Generation / embedding / GPU | PASS: `OK`, 768-d, `100% GPU` for both models |
| Postgres credential / error-handler insert | PASS |
| Webhook RAG: DEPI eligibility question | PASS: exact official answer, 0.9 s (was ~20 s on CPU) |
| Clarification ("admission requirements") | PASS: asks Digilians vs DEPI |
| No-answer (Digilians stipend dates) | PASS: approved no-answer fallback with official portals |
| Dashboard login with rotated password | PASS: role admin, API 200 |
| Executions since regression start | 18/18 success; all-time non-success = 0 |
| Restarts | 0 on all containers |
| Logs (`--tail=100`) | Only two historical Postgres lines: an earlier credential test with a truncated password, and an audit query against a nonexistent table |

**RAG provenance:** `DEBI/scraped_faq` 29 rows and `DEBI/scraped_rag` 7 rows. All have `source_url` on `depi.gov.eg`, a content hash, and a 768-d embedding; 0 rows are non-official or lack a URL. The knowledge base was not modified in this pass, and no Digilians material was ingested.

## 11. Files changed

`deployment/`: `VERSION`, `CHANGELOG.md`, `DEPLOYMENT.md`, `MANIFEST.sha256` (new), `compose/docker-compose.yml`, `scripts/{common,deploy,install_offline,healthcheck,13_initialize_models,set_permissions,generate_checksums,backup}.sh`, `application/ingestion/{Dockerfile,.dockerignore}`, `application/scraper/{Dockerfile,.dockerignore,requirements.runtime.txt}`, `assets/n8n/workflows/0{1,2,3,4A,4B,4C,4D,5,6}_*.json`, `docs/{n8n,ollama,offline_install}.md`; file mode `100644→100755` for all 36 tracked `deployment/**/*.sh`. Root: `docs/operations_runbook.md` (placeholder), `docs/PRODUCTION_HARDENING_REPORT.md` (this file).

## 12. Git commits (local, **not pushed**)

| Commit | Summary |
|---|---|
| `ab47f99` | fix(deployment): reconcile bundle with production server fixes |
| `c5e31e2` | build(deployment): tolerate slow package-index edges in tool image builds |
| (this report) | docs: add production hardening and reconciliation report |

## 13. Remaining blockers / follow-ups

1. **Dashboard forced password change is client-side only.** The API accepts `must_change_password=true` tokens on protected routes, and JWTs (12 h) remain valid after a password change. Enforce server-side and add token revocation (app change; not done here).
2. **Digilians knowledge gap:** no approved Digilians source rows; the bot returns the no-answer fallback.
3. **Backups are on-host only;** off-host encrypted copy and a restore drill in an isolated environment are pending (runbook Step 29).
4. **Git history secret scan** on a full clone before publishing/pushing.
5. **Network path to PyPI** is intermittently stalling; review proxy/CDN routing or use an approved mirror.
6. **Operator hygiene:** move the dashboard admin password into the vault and delete the secret file; rotate the server SSH password and move to key-only SSH.
7. **Phase E not started:** FQDN/TLS (host port 80 is occupied by native nginx), firewall, WhatsApp pairing, acceptance scenarios, Ministry sign-off.
8. Docs contain some bare `docker compose logs …` commands; use `source scripts/common.sh; dc logs …` so the GPU overlay and project directory apply.

## 14. Production readiness impact

The deployment is now **reproducible from the canonical repository**: a clean clone builds and deploys without manual server patches. Server and source are in sync (manifest verified), and the silent CPU fallback path is closed and detected. The two exposed credentials were rotated. **Status remains NOT READY for customer traffic**: Phase E (TLS/FQDN, firewall, WhatsApp E2E), acceptance scenarios, off-host backup and restore drill, and Ministry approval are outstanding.
