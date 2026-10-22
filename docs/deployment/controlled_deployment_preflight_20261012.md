# Controlled deployment preflight — 2026-10-12

## Decision

**Deployment is on hold. No remote files, containers, workflows, databases, or configuration were changed.** The local dashboard candidate passes its focused checks and can be represented as non-ready for RAG. The repository's upgrade procedure requires a protected off-host backup and an isolated restore verification before production deployment. The server currently has only older on-host backups, and no approved off-host vault or isolated restore target was identified. The dashboard-only candidate can be staged for a subsequent controlled update after those prerequisites are available.

## Candidate and local verification

- Project: `E:\NexaServe`
- Branch: `master`
- Candidate commit: `a0b9a5e3d93673b159dc68b81e3a9bb2eda0516d`
- Candidate source working tree was clean before this report was added; this report is the only new untracked artifact.
- Candidate changes are dashboard reporting, Excel exports, their packaging, and a sanitized RAG summary. The latest dashboard commits do not change n8n workflow files or database schemas. Proposed deployment scope is the existing dashboard service only; no knowledge-record ingestion or workflow activation is included.
- Root dashboard and `deployment/application/dashboard` source match by content. `index.html` and `Dockerfile` differ only in line endings.
- Unit/API reporting tests: **25 passed**.
- Deployment runtime-observability tests: **6 passed**.
- `node --check`, Python compilation, `git diff --check`, and Compose configuration validation: passed. Compose validation emitted warnings that the local `.env` does not set `EMBED_MODEL` and `EMBED_DIMENSION`; those values are not used by the dashboard image build.
- Targeted dashboard image build: **passed**. The first local build attempt used the wrong Compose project directory and failed before building; the corrected command used `deployment` as the project directory and built successfully. No container was started locally.

## RAG status

The sanitized artifact at `dashboard/evaluation/rag_evaluation_summary.json` reports **33 passed, 2 failed, 1 blocked, 36 planned**. The source master verdict is `NOT_READY`; runtime identity and corpus version are absent. The evaluation remains blocked and must not be described as answer accuracy or readiness. Summary artifact SHA-256: `BACDBF6618C32DE1C3CB3EA3C715A029428F6AA936579F932E747FA40E0BAD55`.

## Verified Ministry host state (read-only inspection)

- SSH alias `nexaserve-ministry` resolves to the expected `depi@10.179.0.125`; strict host-key checking succeeded. The remote host reported user `depi` and hostname `depi`.
- Existing Compose project: `nexaserve`, rooted at `/opt/nexaserve/deployment`, using `compose/docker-compose.yml` and `compose/docker-compose.gpu.yml`.
- Six containers were running and reported healthy: PostgreSQL, Redis, Ollama, n8n, WhatsApp, and dashboard. No container was restarted.
- Current dashboard image ID: `sha256:dcaf499f19db8627f979ba60ef381641678585f06917ba9d1a278ecf1d19e18b`; created 2026-09-28. The live OpenAPI document reports dashboard version `2.0.0` and 12 paths.
- Deployed bundle version: `0.1.1`. The remote source checkout `/home/depi/NexaServe-src` is clean at `cd918d9`; this differs from the local candidate commit. The deployment target itself was identified from the running Compose labels and actual project configuration.
- Production DB engine is PostgreSQL. This task did not query customer or knowledge rows.

## Workflow scope and limitation

The proposed dashboard-only candidate contains no n8n workflow edits, so no workflow update is proposed. The local workflow bundle has 11 JSON files; the deployed filesystem bundle has 10. SHA-256 values differ for all 10 shared filenames, and `06_output_channel_dispatcher.json` exists only in the local bundle. These differences are outside the dashboard candidate and will not be copied.

The live n8n API could not be inspected: the deployed dashboard container has no `N8N_API_KEY` configured, and a read-only request returned HTTP 401. Therefore active workflow IDs and activation states could not be confirmed from n8n itself. No API key was printed or requested in chat. Any future workflow synchronization requires secure configuration of the approved key on the server, followed by stable-ID comparison and workflow export before changes.

## Backup and rollback readiness

- `/var/lib/nexaserve/backups` is restricted to `depi:depi` with mode `0700`.
- Existing PostgreSQL and n8n dumps and secret-bearing `.env` copies are dated 2026-09-28. A deployment bundle archive is also dated 2026-09-28. These are older than the running deployment and reside on the same server filesystem; no fresh backup was created.
- Repository guidance in `deployment/docs/upgrade.md` and `deployment/docs/backup_restore.md` requires a readable backup, protection of secret-bearing files, transfer to an approved encrypted off-host vault, and a restore test in an isolated recovery environment. No vault destination, restore host, or recent restore evidence was found during this inspection.
- The intended rollback for a dashboard-only change is to retain the current dashboard image and exact prior dashboard bundle, then rebuild/restart only the dashboard service if health checks fail. No rollback point was created because the required backup gate is unresolved.

## Safe proposed change after prerequisites

1. Use the Ministry-approved encrypted off-host vault and isolated restore environment to create and verify fresh backups, including PostgreSQL and n8n databases and protected configuration, before deployment.
2. Record current dashboard image ID and archive the exact existing dashboard application directory with a checksum.
3. Transfer only the reviewed `deployment/application/dashboard` files and sanitized RAG summary; preserve the server's existing Compose files, environment, volumes, and unrelated services.
4. Build and update only the existing `dashboard` Compose service, with dependencies left running. Do not apply migrations or synchronize workflow files.
5. Verify the dashboard health endpoint, authenticated routes, role restrictions, evaluation status, and representative Excel exports; retain the old image and bundle for rollback.

## Items needed to clear the deployment hold

- Ministry-approved encrypted off-host backup destination and access method, plus an isolated restore environment (or recent verified restore evidence accepted by the service owner).
- Confirmation that this release excludes n8n workflow synchronization. If workflow synchronization is expected, first configure the API key through the approved server secret-management path and verify the live inventory; do not send the key in chat.

