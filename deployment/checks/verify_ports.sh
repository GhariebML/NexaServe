#!/usr/bin/env bash
set -Eeuo pipefail
for port in 5432 6379 11434 5678 8080 8090 80 443; do
  if ss -ltn | awk '{print $4}' | grep -Eq "[:.]${port}$"; then echo "Listener present on $port"; else echo "No host listener on $port"; fi
done
echo 'Expected listeners are policy-specific; app-only ports should be loopback, database/cache/model ports private.'
