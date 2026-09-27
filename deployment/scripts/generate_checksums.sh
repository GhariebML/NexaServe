#!/usr/bin/env bash
set -Eeuo pipefail
here="$(cd -- "$(dirname -- "$0")/.." && pwd)"; cd "$here"
find . -type f ! -name MANIFEST.sha256 ! -path './.env' ! -path './offline-package/*' -print0 | sort -z | xargs -0 sha256sum > MANIFEST.sha256
echo "Wrote $here/MANIFEST.sha256"
