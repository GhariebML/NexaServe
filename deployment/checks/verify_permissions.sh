#!/usr/bin/env bash
set -Eeuo pipefail
here="$(cd -- "$(dirname -- "$0")/.." && pwd)"
find "$here/scripts" -type f -name '*.sh' ! -executable -print -quit | grep -q . && { echo 'One or more deployment scripts lack execute permission.'; exit 1; } || true
if [[ -e "$here/.env" ]]; then mode=$(stat -c '%a' "$here/.env"); [[ "$mode" == 600 ]] || { echo '.env must have mode 0600'; exit 1; }; fi
echo 'Permission checks passed.'
