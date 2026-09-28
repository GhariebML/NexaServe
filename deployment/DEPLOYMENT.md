# NexaServe deployment runbook

## 1. What this is

NexaServe is a local-first customer service system. WhatsApp messages enter the Baileys bridge, n8n runs the customer/session/intent/RAG/HITL/output/logger workflows, Ollama serves the chat and embedding models, PostgreSQL 16 with pgvector stores application state and knowledge, Redis supports auxiliary status/cache work, and a FastAPI application serves the operations dashboard.

This folder is the deployment unit. It includes Compose manifests, Linux scripts, canonical workflow exports, the current schema plus additive migrations, the WhatsApp/dashboard application sources, the scraper, and the currently packaged DEPI source data. It does not include runtime credentials, n8n credential records, WhatsApp pairing state, a live database export, or customer records. The bundle does not certify customer-answer quality: the previous runtime audit found model OOM failures and open provenance/WhatsApp checks. It must pass the target acceptance gate before real traffic.

## 2. Target and prerequisites

- Ubuntu Server 24.04 LTS, x86_64; recommended 8+ CPU cores, 32 GiB RAM, and at least 100 GiB free disk.
- NVIDIA GPU with approximately 12 GiB VRAM as a planning baseline. Exact compatibility depends on the detected GPU, driver, model, quantization, context length, and concurrency. Verify real generation; there is no silent CPU fallback.
- Ministry-approved DNS, NTP, firewall rules, TLS certificate/key, and controlled access for administration.
- Online mode needs approved package/image/model registries. Offline mode needs the generated image/model archives and an approved source for Ubuntu/NVIDIA host packages.
- `docker` / Docker Compose v2; `curl`, `jq`, `openssl`, `tar`, `sha256sum`, and `nvidia-smi` for GPU deployment.

## 3. Architecture and exposure

```text
Citizen WhatsApp ↔ Baileys bridge (container: cs-whatsapp; internal :8080)
                              │ POST /webhook/customer-service
                              ▼
                         n8n :5678 ─── Ollama :11434 (qwen2.5:3b)
                           │  └──────── Ollama nomic-embed-text (768)
                           ├─────────── PostgreSQL 16 / pgvector (customerservice + n8n DB)
                           ├─────────── Redis 7
                           └─────────── FastAPI admin dashboard :8090
DEPI scraper → reviewed JSON source → ingestion script → knowledge_base.embedding vector(768)
```

Only localhost-bound admin/service ports are published (n8n 5678, WhatsApp 8080, dashboard 8090); database, Redis and Ollama are internal-only. Optional Nginx exposes 80/443 and requires Ministry-provided TLS files. Restrict `/qr` at the perimeter/VPN because pairing it authorizes a WhatsApp device. Keep n8n editor administration on SSH tunnel or a separately protected internal route; only the webhook path is proxied here. The dashboard's same-origin UI does not need wildcard CORS.

The repository Compose runtime had five containers; this package adds the existing dashboard as a sixth application container, an optional Nginx proxy, and opt-in tools for scraper and ingestion. It does not invent a separate API service. See `docs/architecture.md`.

## 4. Modes

**A — online:** Compose pulls its configured images; builds NexaServe images; `13_initialize_models.sh` downloads `qwen2.5:3b` and `nomic-embed-text`. Host packages/driver/toolkit use the approved Ubuntu/NVIDIA repositories.

**B — offline/restricted:** On a connected Linux builder with the approved runtime bundle and `.env`, run `scripts/prepare_offline_bundle.sh`. It places Docker archives and Ollama model-store archive under `assets/offline/`; copy this entire `deployment/` folder to the target using approved media. Create a fresh target `.env` there; never transfer the builder `.env`. Load archives with `scripts/install_offline.sh`. Host OS/NVIDIA packages are not vendored; use the Ministry's approved apt mirror/package set. Model-store archive must be from the same Ollama release and pass the model generation test after import. Offline mode has not been run on Ubuntu and needs target validation.

## 5. Exact deployment order

Run commands from this directory unless stated. Keep a second administrator session available. Stop if a gate says FAIL; do not open customer traffic.

### Phase A — verify the bundle and host

1. Check transfer integrity: `sha256sum -c MANIFEST.sha256`. Expected: each listed file reports `OK`; a mismatch means recopy the bundle.
2. Make shell scripts executable after transfer: `bash scripts/set_permissions.sh`. Expected: permission confirmation (scripts 0750; container-mounted assets world-readable, Postgres init script 0755). If this fails, stop and check filesystem mount options.
3. Install base tools: `bash scripts/01_install_host_dependencies.sh`. Expected: apt exits 0. On repository/DNS failure, request Ministry mirror access; do not switch to unapproved mirrors.
4. Review Ubuntu and GPU: `cat /etc/os-release; uname -m; lscpu; free -h; df -h /; timedatectl status; nvidia-smi`. Expected Ubuntu 24.04, x86_64, adequate RAM/disk and recognized GPU/driver. If GPU absent, stop GPU deployment; CPU mode is not certified.
5. For a missing driver, ask Ministry IT to approve the correct signed Ubuntu driver. Review `ubuntu-drivers devices`, install the approved/recommended driver with `sudo ubuntu-drivers install`, reboot, then repeat `nvidia-smi`. Do not install a driver `.run` file over package-managed drivers.

### Phase B — Docker and GPU

6. Install Docker Engine/Compose: `bash scripts/02_install_docker.sh`. Expected `docker --version` and `docker compose version`; apt/signature errors mean stop and resolve approved repository setup.
7. Install NVIDIA Container Toolkit: `bash scripts/03_install_nvidia_toolkit.sh`. Expected successful package install and Docker restart. The script uses NVIDIA's signed apt repository and current package candidate; record package versions for change control.
8. Validate passthrough: `bash scripts/verify_gpu.sh`. Expected host and test-container `nvidia-smi` both succeed. If Docker cannot see the device, stop; inspect `/etc/docker/daemon.json`, toolkit config, driver/runtime versions, then restart Docker and retry.
9. Run full preflight: `bash scripts/00_preflight.sh`. It checks Ubuntu/architecture, CPU/RAM, disk display, GPU/driver, Docker/Compose, DNS, NTP, and port listeners. Resolve every FAIL and assess WARN items before continuing.

### Phase C — configure and start

10. Place this folder at the approved server path, recommended `/opt/nexaserve/deployment`; run `cd /opt/nexaserve/deployment`. Keep the release folder immutable after deployment where practical.
11. Generate secrets: `bash scripts/prepare_environment.sh`. It creates `.env` only if absent, with random values and mode 0600. Expected confirmation with no secret values printed. Back up this file through the approved secret vault; losing `N8N_ENCRYPTION_KEY` can make saved n8n credentials unreadable.
12. Edit `.env` using a secure editor. Set `N8N_HOST`, `N8N_PROTOCOL=https`, `WEBHOOK_URL=https://<Ministry-approved-FQDN>/`, timezone, and `TLS_CERT_DIR` to approved values. Do not put an unapproved IP/host in the file. Keep secrets generated in step 11.
13. Check required config without printing it: `docker compose --project-directory "$PWD" --env-file .env -f compose/docker-compose.yml config --quiet`. Expected exit 0. Any missing variable, bind mount, or YAML issue: stop and correct paths/config.
14. Prepare optional backup/diagnostic directory: `sudo NEXASERVE_DATA_ROOT=/var/lib/nexaserve bash scripts/prepare_directories.sh`. Expected directories mode 0750; if your organization owns storage differently, have IT create its approved path and set `NEXASERVE_DATA_ROOT` accordingly.
15. Online deployment: `bash scripts/deploy.sh gpu`. Expected six core containers start. Offline deployment instead: after building on target if necessary, run `bash scripts/install_offline.sh`. Do not run both modes as a migration.
16. Wait for health: `bash scripts/healthcheck.sh`. It checks container health and pgvector. A pass means services answered their health probes only; it does not prove model generation, workflow routing, RAG, or WhatsApp delivery.

### Phase D — models, database, workflows and dashboard

17. Check schema: `bash scripts/smoke.sh`. Expected pgvector, pg_trgm, uuid-ossp, migration ledger, active KB/embedding counts, and `ollama list`. Fresh DB creation only occurs with a new empty PostgreSQL volume. Existing volumes are never reset. For existing DBs, take a verified backup first, then run `bash scripts/migrate.sh` and inspect its output.
18. Download models in online mode: `bash scripts/13_initialize_models.sh`. Expected: models present, container generation OK, embedding dimension 768, and `100% GPU`; the script tests the Compose Ollama service, never a host Ollama, and exits non-zero on failure. If generation fails, inspect `docker compose logs ollama`, host RAM/VRAM, and GPU use; do not claim readiness from `ollama list`.
19. Establish the n8n owner account in the n8n UI via a localhost SSH tunnel, e.g. `ssh -L 5678:127.0.0.1:5678 <admin>@<server>`. Open `http://127.0.0.1:5678`. Use Ministry credential policy; no default account is supplied.
20. In n8n create a PostgreSQL credential for host `postgres`, port `5432`, database `customerservice`, user `cs_app_user`, password from `.env`; create a second credential only if a workflow explicitly requires the n8n DB. Never copy the local credential export. Assign the credential to every Postgres node.
21. Import canonical workflow JSON: `bash scripts/deploy_workflows.sh`. Workflow exports are inactive and local credential IDs were removed. Confirm every node's credential, Ollama URL, WhatsApp URL, internal workflow ID/call, and webhook path in n8n; resolve import errors before activating. Activate only the reviewed core gateway and required subworkflows after a backup/export.
22. Test gateway from a trusted host through the SSH tunnel: `curl -fsS -X POST http://127.0.0.1:5678/webhook/customer-service -H 'Content-Type: application/json' --data '{"customer_message":"ما هي شروط الالتحاق برواد مصر الرقمية؟","channel":"webchat","session_id":"deployment-smoke-01"}'`. Expected structured response in Arabic grounded in the official DEPI source. HTTP 200 alone is not a pass; correlate execution, retrieval evidence, source URL, model result, validator, DB log and exact response. Do not replay real customer PII.
23. Build dashboard, create its first operator account interactively: `bash scripts/create_dashboard_admin.sh`; then open `http://127.0.0.1:8090` via SSH tunnel. Test login, role permissions, and password change. Stop if migration/table/query errors appear.
24. Review and refresh official source data if its crawl age exceeds Ministry policy: `bash scripts/refresh_sources.sh`. The script asks before DB ingestion. Inspect scraped URLs and extraction before typing `INGEST`. Run a test query after every ingest and check `source_url`, hash and 768-dimension embeddings. Digilians content needs independently reviewed official source material; the packaged scrape is DEPI only.

### Phase E — network, WhatsApp and acceptance

25. Obtain the Ministry FQDN, TLS chain/key, DNS, load balancer and source allow-list from IT. Place fullchain and key in the protected `TLS_CERT_DIR`; verify key ownership/mode. Do not copy TLS private keys into this bundle.
26. Optional proxy: `docker compose --project-directory "$PWD" --env-file .env -f compose/docker-compose.yml --profile proxy up -d proxy`. Verify HTTPS certificate, dashboard same-origin, webhook delivery, and access controls. Firewall should allow only approved ingress to 443 (and 80 only for redirect/certificate policy); keep 5678/5432/6379/8080/8090/11434 off public interfaces. `/qr` must be VPN/IP restricted.
27. Pair WhatsApp at `https://<approved-FQDN>/qr` only on a controlled admin network. Verify connection state, send a test from an approved test handset, then correlate bridge log → n8n execution → retrieval/model → database message → exact delivered WhatsApp text. A healthy bridge is not proof of outbound E2E.
28. Exercise one FAQ, paraphrase, ambiguous, no-answer, prompt-injection, cross-program, human escalation, restart, and memory follow-up case. Preserve redacted IDs/results; check answer facts/program/language/source, execution nodes, errors, latency, and logs. Never weaken quality criteria to get a pass.
29. Run `bash scripts/backup.sh`; move output to encrypted off-host storage and perform a restore drill in an isolated environment before production. Use `bash scripts/collect_diagnostics.sh` only when needed; review diagnostics before sharing.
30. Final gate: require all items in `docs/operations_runbook.md`, documented WhatsApp test, verified restore, source freshness, zero unresolved P0 answer defects, alerting/owner handoff, and Ministry approval. Current package status is **NOT READY until these target checks pass**.

## 6. Firewall, backup and rollback

Keep database/cache/model ports private. Permit egress only to approved registries, Ministry repositories, DNS/NTP, and official source domains when online. See `docs/networking.md`, `docs/firewall.md`, and `docs/reverse_proxy.md`.

Backups include application and n8n databases. They contain sensitive data and secrets and must be encrypted, access-controlled, retained per policy, and stored off-host. Also back up n8n/WhatsApp/Ollama named volumes consistently; never copy a live PostgreSQL data directory as a backup. Test restore using `scripts/restore.sh` against a designated recovery environment.

For upgrade: remove public traffic, back up, preserve bundle/image digests, apply additive migrations, deploy, and run acceptance checks. To roll back, stop ingress and use the previous approved bundle and verified database backup if the migration is incompatible. `scripts/rollback.sh` is a checklist guard and does not delete volumes or automatically reverse SQL.

## 7. Troubleshooting and stop conditions

- **Wrong Ubuntu/architecture, GPU absent, driver/toolkit mismatch:** stop. Ministry IT must provision supported Ubuntu x86_64, driver and toolkit. Never silently use CPU inference.
- **Docker unavailable/permission denied:** inspect `systemctl status docker`, `journalctl -u docker`, and `docker compose version`; use `sudo` according to policy. Docker group is root-equivalent.
- **Port occupied:** inspect `sudo ss -ltnp`; change localhost port variables or resolve service ownership before starting. Do not expose DB/model ports to fix a conflict.
- **PostgreSQL unhealthy / pgvector missing:** inspect `docker compose logs postgres`; verify new-volume initialization and `vector` extension. Never delete a volume. Existing data requires a backup and reviewed migration.
- **Redis unhealthy:** check `docker compose logs redis`, configured password and ACL/network. Do not disable authentication.
- **Ollama/model unavailable or GPU not used:** `docker compose logs ollama; docker compose exec ollama ollama list; nvidia-smi`. Repeat an actual generation test. If OOM occurs, stop release acceptance; measure prompt/context, GPU/RAM and concurrent requests before changing model.
- **n8n inaccessible or workflow inactive:** verify localhost port/tunnel, n8n health, workflow activation, credential assignment, webhook URL, workflow sub-IDs and execution details. Do not activate credentialless exports.
- **WhatsApp QR/disconnect:** check approved network access, phone linking limits and persistent `whatsapp-auth` volume. Preserve auth state; do not copy it into the deployment package or diagnostics.
- **Dashboard/auth failure:** inspect dashboard logs, `admin_users` migration, DB grants, `DASHBOARD_JWT_SECRET`, and the operator account. Use the account creation helper; no default password exists.
- **Proxy/TLS/firewall failure:** check certificate SAN/chain/key pairing, `docker compose logs proxy`, DNS, ingress rules and upstream health. Restrict QR and admin UI.
- **Disk pressure:** inspect `df -h`, Docker usage and approved retention. Do not run `docker system prune --volumes` or delete customer data.
- **Restore/migration/rollback failure:** stop ingress; preserve current volumes and logs; escalate to the DB/platform owner. Do not improvise destructive SQL.

## 8. Target-side unknowns

Ministry IT must provide approved host/GPU model and driver, DNS/FQDN, TLS, inbound/outbound network policy, SSH/admin identities, secret vault, backup target/retention, WhatsApp account/phone and approved test recipient, official Digilians source/content, n8n admin ownership, monitoring/alert contacts, and change-window approval. The platform owner must approve model load, accuracy, Arabic quality, concurrency, VRAM, and service-level targets.
