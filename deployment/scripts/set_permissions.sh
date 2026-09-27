#!/usr/bin/env bash
set -Eeuo pipefail
here="$(cd -- "$(dirname -- "$0")/.." && pwd)"
find "$here/scripts" "$here/assets/postgres" -type f -name '*.sh' -exec chmod 0750 {} +
echo 'Shell scripts now have owner/group execute permissions.'
