# Upgrade procedure

1. Schedule change window; block ingress and record release/image/model versions.
2. Run `scripts/backup.sh`; verify dump readability and protect secret-bearing output.
3. Preserve current bundle and Compose/image digests. Review workflow JSON diff and migration SQL.
4. Apply only reviewed additive migration with `scripts/migrate.sh`; do not drop/recreate volumes.
5. Deploy approved new bundle and run health, generation, retrieval, workflow, dashboard, HITL and WhatsApp acceptance.
6. Reopen traffic only after owner sign-off; monitor errors, OOM, latency and data consistency.

Use `docs/rollback.md` if any gate fails. This bundle does not provide automatic reverse migrations.
