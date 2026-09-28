# Changelog

## 0.1.1 — 2026-09-28

Production reconciliation of fixes first applied by hand on the target server.

- Compose: bind mounts and build contexts use `./` paths relative to the deployment folder, which every script and runbook command passes as `--project-directory` (the `../` paths resolved outside the bundle).
- `scripts/common.sh`: `dc()` always applies the GPU overlay (`NEXASERVE_OFFLINE=1` adds the offline overlay). Previously any `dc` call such as `refresh_sources.sh`/`kb-ingest` recreated Ollama without its GPU reservation (silent CPU fallback). `deploy.sh`/`install_offline.sh` use `dc`.
- `scripts/healthcheck.sh`: fails when the Ollama container has no GPU reservation.
- `scripts/set_permissions.sh`: container-mounted assets stay world-readable (0644, Postgres init scripts 0755); the previous 0750 made `init-databases.sh` unreadable by the Postgres container, so first-boot database/role creation was skipped. Shell scripts are tracked executable in Git.
- `scripts/13_initialize_models.sh`: validates generation and 768-d embeddings against the Compose Ollama service over the internal network (never a host Ollama on 127.0.0.1:11434), checks GPU placement, pulls only missing models (offline-safe), and exits non-zero on failure. `MODEL_CHAT`, `MODEL_EMBED`, `EXPECT_DIM` override for testing.
- Ingestion image: builds from the canonical layout (`scripts/db_config.py`); no longer copies gitignored `DEPI_Web_Scraper/data/final/`.
- Scraper image: pins `playwright==1.63.0` to match the base image; no longer copies gitignored `data/final/`. Scrape output lives only in the `source-data` volume.
- `.dockerignore` for ingestion/scraper contexts excludes `.env`, caches and data.
- `generate_checksums.sh` refuses to fingerprint secrets/dumps/auth state and skips caches/logs; `MANIFEST.sha256` is now shipped.
- Canonical workflows set `errorWorkflow` to the Global Error Handler (`CSWF000000000008`).

## 0.1.0 — 2026-09-28

- Initial Linux deployment candidate from the audited NexaServe source tree.
- Includes Compose, GPU overlay, offline image/model preparation, schema and additive dashboard-user migration, canonical core workflows, dashboard/WhatsApp source, RAG/scraper files, scripts, and runbooks.
- Excludes runtime secrets, database exports, n8n credentials, WhatsApp auth, and customer data.
- Known blockers remain; see `BUILD_REPORT.md` and `DEPLOYMENT.md`.
