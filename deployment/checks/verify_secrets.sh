#!/usr/bin/env bash
set -Eeuo pipefail
here="$(cd -- "$(dirname -- "$0")/.." && pwd)"
python3 "$here/checks/verify_secrets.py" "$here"
