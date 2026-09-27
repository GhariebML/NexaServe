# Operations runbook

## Daily/shift checks

- Run `scripts/healthcheck.sh` and inspect Docker state. Then review n8n failures, Ollama generation/OOM, PostgreSQL storage/connections, WhatsApp connection, dashboard login, TLS expiry and host disk/GPU.
- Health probes do not certify answer correctness. Sample requests must record program, retrieved record/source, model context/output, validator and exact delivered text with correlated request/conversation/execution IDs.
- Escalate no-answer/hallucination, cross-program leakage, OOM, DB integrity, QR exposure or lost correlation as P0; disable affected route and use human support while investigating.

## Scheduled work

- Backup databases per approved RPO; separately capture named volumes consistently and retain an encrypted off-host copy. Perform restore drills at an approved cadence.
- Refresh official web data only on approved domains. Review page URL/hash/extraction before ingest; record crawl/ingestion time and owner. Current app records do not carry full per-record embed-model/timestamp provenance.
- Patch Ubuntu, Docker, NVIDIA driver/toolkit, base images and model tags through change control. Record image digests/model manifests and schedule reboot windows.
- Review n8n audit, credentials, inactive/duplicate workflows, admin roles, firewall/TLS and backup restore evidence.

## Incident response

1. Contain at ingress; do not destroy volumes.
2. Collect privacy-reviewed `scripts/collect_diagnostics.sh` output and correlated n8n execution IDs.
3. Preserve DB snapshot/backup and exact bundle, workflow revision, model digest and timestamps.
4. Restore service only after a controlled fix, regression and owner sign-off; use rollback plan if needed.

See `../DEPLOYMENT.md` troubleshooting and backup procedures.
