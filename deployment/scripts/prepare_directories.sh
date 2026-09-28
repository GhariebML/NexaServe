#!/usr/bin/env bash
set -Eeuo pipefail
base="${NEXASERVE_DATA_ROOT:-/var/lib/nexaserve}"
sudo install -d -m 0750 -o "${SUDO_USER:-$USER}" -g "${SUDO_USER:-$USER}" "$base" "$base/backups" "$base/diagnostics"
echo "Prepared $base. Compose named volumes are managed by Docker."
