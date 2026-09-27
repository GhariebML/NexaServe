#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname -- "$0")/common.sh"
require_env
chat=$(grep '^OLLAMA_MODEL=' "$ENV_FILE"|cut -d= -f2-)
embed=$(grep '^EMBED_MODEL=' "$ENV_FILE"|cut -d= -f2-)
dc exec ollama ollama pull "$chat"
dc exec ollama ollama pull "$embed"
curl -fsS http://127.0.0.1:11434/api/generate -H 'Content-Type: application/json' -d "{\"model\":\"$chat\",\"prompt\":\"Reply with the single word OK.\",\"stream\":false,\"options\":{\"num_predict\":16}}" | jq -e '.response|length>0' >/dev/null
echo 'Generation smoke request passed. Test Arabic grounding, latency, VRAM and OOM behavior before use.'
