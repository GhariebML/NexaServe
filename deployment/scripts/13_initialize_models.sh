#!/usr/bin/env bash
# Pull (if missing) and validate the models served by the Compose `ollama` service.
# All requests go to the container service over the internal network (http://ollama:11434)
# from the n8n container, i.e. the same path the workflows use. A native host Ollama on
# 127.0.0.1:11434 is never contacted. Exits non-zero on any failure.
set -Eeuo pipefail
source "$(dirname -- "$0")/common.sh"
require_env
chat="${MODEL_CHAT:-$(env_value OLLAMA_MODEL)}"
embed="${MODEL_EMBED:-$(env_value EMBED_MODEL)}"
dim="${EXPECT_DIM:-$(env_value EMBED_DIMENSION)}"
fail() { echo "FAIL: $*" >&2; exit 1; }

for model in "$chat" "$embed"; do
  if dc exec -T ollama ollama show "$model" >/dev/null 2>&1; then echo "Model present: $model"
  else echo "Pulling $model"; dc exec -T ollama ollama pull "$model" || fail "pull of $model failed"; fi
done

post() { dc exec -T n8n wget -qO- -T 300 --header 'Content-Type: application/json' --post-data "$2" "http://ollama:11434/api/$1"; }

gen=$(post generate "{\"model\":\"$chat\",\"prompt\":\"Reply with the single word OK.\",\"stream\":false,\"options\":{\"num_predict\":16}}") \
  || fail "generation request to container Ollama failed"
jq -e '.response|length>0' >/dev/null <<<"$gen" || fail "empty generation response"
echo "Generation OK ($chat): $(jq -r '.response' <<<"$gen" | head -c 40)"

emb=$(post embed "{\"model\":\"$embed\",\"input\":\"اختبار التضمين embedding test\"}") \
  || fail "embedding request to container Ollama failed"
got=$(jq '.embeddings[0]|length' <<<"$emb")
[[ "$got" == "$dim" ]] || fail "embedding dimension $got, expected $dim"
echo "Embedding OK ($embed): dimension $got"

[[ "$(docker inspect -f '{{json .HostConfig.DeviceRequests}}' "$(dc ps -q ollama)")" == *gpu* ]] \
  || fail "ollama container has no GPU device reservation"
proc=$(dc exec -T ollama ollama ps | awk -v m="$chat" 'index($1, m)==1')
[[ "$proc" == *"100% GPU"* ]] || fail "$chat is not fully on GPU: ${proc:-not loaded}"
echo "GPU inference OK: $chat 100% GPU"
echo 'Model validation passed. Test Arabic grounding, latency, VRAM and OOM behavior before use.'
