#!/usr/bin/env bash
set -Eeuo pipefail
here="$(cd -- "$(dirname -- "$0")/.." && pwd)"
# Operator scripts: owner/group only.
find "$here/scripts" "$here/checks" "$here/tests" -type f -name '*.sh' -exec chmod 0750 {} +
# Files bind-mounted read-only into containers run as other UIDs (postgres 999, redis 999,
# node 1000, nginx 101) must be world-readable; never group/world-writable.
find "$here/assets" "$here/migrations" "$here/config" -type d -exec chmod 0755 {} +
find "$here/assets" "$here/migrations" "$here/config" -type f -exec chmod 0644 {} +
# The postgres entrypoint executes init scripts that are executable (sources them otherwise).
find "$here/assets/postgres" -type f -name '*.sh' -exec chmod 0755 {} +
[[ ! -f "$here/.env" ]] || chmod 0600 "$here/.env"
echo 'Permissions set: scripts 0750; container-mounted assets 0644 (init scripts 0755); .env 0600.'
