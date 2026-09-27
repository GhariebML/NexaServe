# Environment and secrets

Run `scripts/prepare_environment.sh`; it generates random 256-bit hex secrets into `.env`, refuses overwrite, suppresses values, and chmods the file 0600. Back up the n8n encryption key with the secret vault; its loss can strand encrypted n8n credentials. Set public `N8N_HOST`, protocol, webhook URL, timezone, and certificate path according to Ministry DNS/TLS.

The example has no usable password. Never copy a workstation `.env`, WhatsApp auth folder, credential export, or production secret. `docker compose config` output may contain secrets: use `--quiet` and don't paste rendered config into tickets.
