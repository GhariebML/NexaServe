# Troubleshooting

See the failure-specific stop gates in `../DEPLOYMENT.md`. Useful read-only checks:

- OS/GPU: `cat /etc/os-release; uname -m; nvidia-smi`; use supported Ubuntu driver and toolkit.
- Docker/ports/disk: `systemctl status docker; docker compose ps; sudo ss -ltnp; df -h`.
- Service: `docker compose logs --tail 200 <service>`; never attach unredacted logs to tickets.
- PostgreSQL/pgvector: `docker compose exec postgres psql -U <admin-user> -d customerservice -c 'SELECT extname FROM pg_extension;'`.
- Ollama: `docker compose exec ollama ollama list`; then actual `/api/generate` and `nvidia-smi` check. OOM means stop acceptance.
- n8n: inspect workflow execution detail, node input/output, credential status and subworkflow ID. A healthy `/healthz` is not an E2E pass.
- WhatsApp: check QR, network/account state and persistent auth volume; preserve session.
- TLS: verify FQDN, chain, expiry, private-key permissions and proxy upstream status.

For DB migration, restore or rollback failure, preserve state and escalate to platform/DB owner; never delete volumes as a troubleshooting shortcut.
