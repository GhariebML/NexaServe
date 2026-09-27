#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname -- "$0")/common.sh"
require_env
out="${1:-${NEXASERVE_DATA_ROOT:-/var/lib/nexaserve}/diagnostics/$(date -u +%Y%m%d-%H%M%S)}"
install -d -m 0700 "$out"
dc ps > "$out/compose-ps.txt" 2>&1 || true
for s in postgres redis ollama n8n whatsapp dashboard; do
  dc logs --tail 150 "$s" 2>&1 | sed -E 's/(PASSWORD|TOKEN|SECRET|API_KEY)=([^ ]+)/\1=[REDACTED]/Ig' > "$out/$s.log" || true
done
{ uname -a; df -h; free -h; nvidia-smi 2>&1 || true; docker version 2>&1 | head -30; } > "$out/host.txt"
echo "Diagnostics saved at $out. Review before sharing; logs may contain customer and operational details."
