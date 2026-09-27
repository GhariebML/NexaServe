# Quickstart

For a connected Ubuntu 24.04 x86_64 server with Docker installed and a working NVIDIA runtime:

```bash
cd deployment
./scripts/00_preflight.sh
./scripts/prepare_environment.sh
./scripts/deploy.sh gpu
./scripts/healthcheck.sh
./scripts/smoke.sh
```

Read [DEPLOYMENT.md](DEPLOYMENT.md) fully first. Configure TLS/firewall, set up the admin account, pair WhatsApp, deploy/activate workflows after credential setup, load/verify models, ingest reviewed knowledge, back up, and obtain Ministry sign-off.
