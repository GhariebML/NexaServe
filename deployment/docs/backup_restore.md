# Backup and restore

Run `scripts/backup.sh` for custom-format dumps of `customerservice` and n8n DB. It also copies `.env` into the output, so the backup is secret-bearing: protect/encrypt and transfer to an approved off-host vault. Back up named volumes for WhatsApp auth, n8n binary/settings, Ollama models and Redis according to policy, using an application-consistent procedure; do not archive live PostgreSQL data files.

Test `scripts/restore.sh CUSTOMER_SERVICE.dump N8N.dump` only in an isolated recovery environment after a verified pre-restore snapshot. Script requires typing `RESTORE`; validate schemas, row counts, workflow credentials, generation, KB source lineage, and WhatsApp pairing strategy. Set RPO/RTO and retention with Ministry IT.
