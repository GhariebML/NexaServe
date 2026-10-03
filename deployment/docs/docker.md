# Docker Engine

Install Engine and Compose v2 with `scripts/02_install_docker.sh`, then check `docker --version`, `docker compose version`, and `systemctl status docker`. Compose defines health checks, restart policies, internal network, persistent named volumes and loopback-only admin ports.

The install script follows the [official Docker Engine Ubuntu instructions](https://docs.docker.com/engine/install/ubuntu/); use the Ministry-approved signed repository mirror where required.

Docker daemon/group control is root-equivalent. Prefer `sudo docker` unless Ministry policy approves membership. Database, Redis and Ollama have no host-published ports. Run `docker compose config --quiet` before deployment.

Container logs use bounded `json-file` rotation (10 MiB × 5 files per service). No CPU/RAM cgroup limits are hard-coded: select safe limits from a target pilot that includes Arabic inference and expected concurrency, while monitoring host RAM/VRAM and OOM events.
