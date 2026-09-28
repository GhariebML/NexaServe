#!/usr/bin/env bash
set -Eeuo pipefail
df -h "${NEXASERVE_DATA_ROOT:-/var/lib/nexaserve}"
avail_kb=$(df -Pk "${NEXASERVE_DATA_ROOT:-/var/lib/nexaserve}" | awk 'NR==2 {print $4}')
min_kb=$((100 * 1024 * 1024))
(( avail_kb >= min_kb )) || { echo 'Less than 100 GiB available; resolve storage plan before deployment.' >&2; exit 1; }
