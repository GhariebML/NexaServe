#!/usr/bin/env bash
set -Eeuo pipefail
here="$(cd -- "$(dirname -- "$0")/../.." && pwd)"
bash "$here/scripts/healthcheck.sh"
bash "$here/scripts/smoke.sh"
