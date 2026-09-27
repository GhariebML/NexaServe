#!/usr/bin/env bash
set -Eeuo pipefail
fail=0
echo 'NexaServe host preflight (read-only)'
if [[ -r /etc/os-release ]]; then . /etc/os-release; printf 'OS: %s\n' "${PRETTY_NAME:-unknown}"; [[ "${ID:-}" == ubuntu && "${VERSION_ID:-}" == 24.04 ]] || { echo 'FAIL: target is Ubuntu 24.04 LTS'; fail=1; }; else echo 'FAIL: cannot read /etc/os-release'; fail=1; fi
arch=$(uname -m); echo "Architecture: $arch"; [[ "$arch" == x86_64 ]] || fail=1
cores=$(nproc 2>/dev/null || echo 0); ram_kb=$(awk '/MemTotal/{print $2}' /proc/meminfo); ram_gb=$((ram_kb/1024/1024)); echo "CPU cores: $cores; RAM: ${ram_gb} GiB"; (( cores >= 8 )) || echo 'WARN: fewer than 8 CPU cores'; (( ram_gb >= 32 )) || echo 'WARN: below 32 GiB RAM baseline'
df -h /; echo "Kernel: $(uname -r)"; swapon --show || true
free_kb=$(df -Pk / | awk 'NR==2 {print $4}'); (( free_kb >= 104857600 )) || { echo 'WARN: less than 100 GiB free on /'; }
if command -v nvidia-smi >/dev/null; then nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader || { echo 'FAIL: nvidia-smi failed'; fail=1; }; else echo 'FAIL: NVIDIA GPU/driver not detected. CPU inference is not certified and no silent fallback is allowed.'; fail=1; fi
docker --version || { echo 'FAIL: Docker Engine missing'; fail=1; }
docker compose version || { echo 'FAIL: Compose plugin missing'; fail=1; }
command -v timedatectl >/dev/null && timedatectl status | sed -n '1,8p' || echo 'WARN: timedatectl missing'
for host in registry-1.docker.io docker.n8n.io ollama.com depi.gov.eg; do getent hosts "$host" >/dev/null && echo "DNS OK: $host" || echo "WARN: DNS unavailable for $host"; done
for url in https://registry-1.docker.io/v2/ https://ollama.com; do code=$(curl --max-time 8 -sS -o /dev/null -w '%{http_code}' "$url" || true); [[ -n "$code" && "$code" != 000 ]] && echo "HTTPS reachable: $url ($code)" || echo "WARN: HTTPS not reachable: $url"; done
for port in 80 443 5678 5432 6379 8080 8090 11434; do ss -ltn 2>/dev/null | awk '{print $4}' | grep -Eq "[:.]${port}$" && echo "WARN: port $port already has a listener" || true; done
if command -v timedatectl >/dev/null; then synchronized=$(timedatectl show -p NTPSynchronized --value 2>/dev/null || echo unknown); [[ "$synchronized" == yes ]] || echo "WARN: NTP not synchronized ($synchronized)"; fi
(( fail == 0 )) || exit 1
echo 'Preflight passed; review warnings and Ministry network policy before installation.'
