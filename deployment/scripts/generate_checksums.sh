#!/usr/bin/env bash
set -Eeuo pipefail
here="$(cd -- "$(dirname -- "$0")/.." && pwd)"; cd "$here"
# Refuse to fingerprint (and thereby bless for transfer) runtime secrets or data.
if find . -type f \( -name '*credentials.json' -o -name '*.dump' -o -name '*.secret' -o -name '*.pem' -o -name '*.key' -o -path '*/auth/*' \) | grep -q .; then
  echo 'Sensitive runtime artifact found in the bundle; remove it before generating the manifest.' >&2; exit 1
fi
find . -type f ! -name MANIFEST.sha256 ! -path './.env' ! -path './offline-package/*' \
  ! -path '*/__pycache__/*' ! -name '*.pyc' ! -name '*.log' -print0 | sort -z | xargs -0 sha256sum > MANIFEST.sha256
echo "Wrote $here/MANIFEST.sha256"
