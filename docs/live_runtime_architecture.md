# Live Runtime Architecture

Snapshot: 2026-09-27, Africa/Cairo. Evidence is from the live n8n execution database, Docker health endpoints, PostgreSQL, and synthetic webchat replays. Workflow IDs/names are listed in [n8n_workflow_inventory.md](n8n_workflow_inventory.md). No real WhatsApp test message was sent.

## Observed customer path

`WhatsApp → cs-whatsapp gateway → n8n Master 01 → Session 02 → Intent 03 → route → FAQ 04B / other handler → Output 06 → Logger 05 → channel delivery`

| Step | Workflow / node | Input observed | Output observed | Status / error behavior |
|---|---|---|---|---|
| WhatsApp ingress | `cs-whatsapp` `/webhook` / n8n `Webhook Ingress` | WhatsApp inbound payload; synthetic audit cases used `channel=webchat` | webhook body | Bridge health was healthy. A real inbound WhatsApp execution existed in baseline history; no controlled outbound WhatsApp message was sent. |
| Gateway | Master 01, `Channel Ingress & PII Sanitizer` | raw body, channel/message/user fields | normalized text, masked text, locale, channel user | Executed in synthetic executions. Earlier webchat identity defaulted every visitor to `web-anon`; patched to honor session/user/request ID or generate a unique ID. |
| Session | SubWF 02 | normalized message, channel identity | customer, conversation, history | Completed in execution 6125. Session context was preserved for FAQ calls. |
| Intent | SubWF 03 | message + session | `ai_output.intent`, confidence/entities | Completed in execution 6126. Historical Ollama classifier requests timed out at ~45 sec and fell back to general support; deterministic FAQ fallback is now in the active workflow. |
| Route | Master 01, `Route by Intent` | intent output | branch 04A / 04B / 04C / general | The DEPI FAQ and comparison traces reached 04B. Intent labeled the comparison query `faq_query`; 04B’s own resolver correctly set `program_scope=COMPARISON`. |
| RAG | SubWF 04B, detector → embedding → bilingual SQL → formatter | message, program filter, 768-D vector | top 5 records, score/context | Fixed request body from JSON array to object/string expression; formatter now consumes all Postgres rows. Query scores and exact source evidence are captured in `logs/runtime_forensic/official_faq_trace.json`. |
| LLM | 04B, `Qwen RAG Grounded Response` | system instructions + `rag_context` + user question | expected JSON answer | Request now reaches Ollama, but `qwen2.5:3b`’s llama-server is killed by the host memory limit. The guardrail returns the stored top-record answer. This is not a successful LLM-grounded answer. |
| Guardrail | 04B, `Guardrail & Professional Formatter` | LLM output or curated fallback | final reply and validation fields | On the captured official FAQ replay, the guardrail preserved the exact official FAQ answer after the LLM process failed. |
| Output | SubWF 06, `Route by Channel` | assembled final response | WhatsApp / Telegram / email / webchat format | Subworkflow ran in synthetic executions. Webchat response is returned by `Respond to Ingress Webhook`; WhatsApp send node was not exercised by a real test. HTTP send is configured with 5s timeout and continue-on-fail. |
| Logger | SubWF 05 | normalized customer message + final reply | customer/AI messages and audit row | Verified in execution 6118: response text equals AI message row; request and parent execution IDs are now attached. |
| Customer response | Master 01, `Respond to Ingress Webhook` | assembled response | exact HTTP JSON reply | Verified for webchat. Does not prove WhatsApp delivery. |

## Runtime conditions

- All five Compose services were healthy before and after the two graceful n8n restarts. n8n `/healthz` returned 200.
- Docker health did not detect the unavailable generation model. `cs-ollama` was healthy and listed the model tag while `/api/generate` returned 500 and `llama-server process has terminated: signal: killed`.
- The host reports about 3.25 GiB total Docker memory. Ollama’s generation subprocess was OOM-killed; `/sys/fs/cgroup/memory.events` now shows 31 `oom_kill` events. The model was absent from `/api/ps` after failure. This blocks production answer quality.
- An overload replay produced HTTP 503 `Database is not ready!`; a sequential replay after recovery returned 200. This failure mode needs a controlled capacity/retry fix before normalizing concurrency.
- No production database was reset; no Docker volume or KB row was deleted.
- Final published active 04B version: `d3eb1aec-83c5-4c3f-a778-9c4a60a059ee`. Post-reload clarification execution 6134 completed and logger/audit IDs matched.
