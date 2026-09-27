#!/usr/bin/env bash
set -Eeuo pipefail
here="$(cd -- "$(dirname -- "$0")/.." && pwd)"; cd "$here"
[[ -f MANIFEST.sha256 ]] || { echo 'MANIFEST.sha256 missing; run scripts/generate_checksums.sh'; exit 1; }
sha256sum -c MANIFEST.sha256
if find . -type f \( -name '*credentials.json' -o -name '*.dump' -o -path '*/auth/*' \) | grep -q .; then echo 'Sensitive runtime artifact found.' >&2; exit 1; fi
