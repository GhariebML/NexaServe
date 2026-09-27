#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname -- "$0")/common.sh"
require_env
dc --profile tools build scraper kb-ingest
dc --profile tools run --rm scraper
echo 'Scrape written to shared source-data volume. Review source URLs, record counts and text before ingestion.'
read -r -p 'Type INGEST to embed and upsert this DEPI scrape into PostgreSQL: ' ack
[[ "$ack" == INGEST ]] || { echo 'Scrape retained; ingestion skipped.'; exit 0; }
dc --profile tools run --rm kb-ingest
echo 'Verify active rows, source_url, content hashes and 768-dimensional embeddings.'
