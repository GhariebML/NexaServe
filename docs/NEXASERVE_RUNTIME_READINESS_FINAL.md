# NexaServe Runtime Readiness — Final

**Status: NOT READY**

## Decision evidence

| Acceptance check | Result | Evidence |
|---|---|---|
| Critical workflows execute | Partial | Synthetic execution 6124 completed through 01/02/03/04B/06/05. |
| No broken nodes | Fail | Qwen generation subprocess killed; 26/30 concurrent requests received HTTP 503. |
| Official FAQ verified | Partial pass | Official DEPI FAQ file → DB id 101 → retrieval rank 1 → context → exact fallback answer. |
| Official scraped content verified | Partial pass | 29 FAQ + 7 page chunks have DEPI source URL; one FAQ replay matched. |
| Correct retrieval | Partial pass | Post-fix replay selected intended topic rows and produced 0 opposite-program top-10 leakage; final LLM answer remains unverified. |
| Correct LLM context | Context pass, generation fail | Correct exact fact appears in context, but model did not return an answer. |
| Correct LLM response | Fail / unverified | HTTP 500, llama-server killed. Final answer came from fallback. |
| Validator preserves correct answer | Pass in captured fallback | Guardrail preserved exact scraped FAQ answer. |
| Arabic quality | Partial | Correct Arabic clarification and fact fallback; scholarship query received irrelevant training duration. |
| DEPI/Digilians isolation | Partial | DEBI SQL filter worked; 0% cross-program leakage not established. |
| Memory | Fail before patch; partial after | Shared `web-anon` identity fixed. Continuity requires client stable session ID; full follow-up test blocked. |
| WhatsApp | Not verified end-to-end | Bridge health was healthy and real inbound execution exists; no controlled outbound message sent. |
| Logs correlated | Pass for synthetic post-fix probe | Latest request ID and master execution 6134 match webhook, both message rows, and audit row. |
| Freshness | Partial | Fresh DEPI scrape and ingestion completed; Digilians source freshness and historical row lineage unverified. |
| No P0 response-quality issues | Fail | Qwen OOM, irrelevant answer, 503 capacity failures, missing legacy provenance. |

## Blocking work

1. Raise/allocate adequate memory for Ollama generation or benchmark a model that fits the existing host. Do not deploy a replacement until Arabic accuracy, groundedness, latency, and memory are compared.
2. Rerun the 30-case suite sequentially after model stability; record retrieval, source, prompt/context, generation, validator, logger, and response per request.
3. Establish and document an official Digilians source and map all 26 rows; validate the COMMON comparison record against primary sources.
4. Add hash/model/timestamp provenance for existing 36 rows that currently lack source URL/hash. Re-embed only rows where content/vector mismatch is established.
5. Send a controlled WhatsApp message only under an approved test recipient/process, then correlate gateway, n8n execution, DB row, Ollama request, and delivered text. Current evidence is webchat only.
6. Verify stable client session IDs and memory follow-up; anonymous clients without a stable ID now get per-request isolation but no cross-turn memory.

## Latest live runtime check

The final post-deployment ambiguous probe completed after correcting the 04B duplicate declaration found in execution 6133. Execution 6134 returned HTTP 200 with the Arabic clarification; 6135/6136/6137/6138/6139 completed through session, intent, RAG, output, and logger. Message content exactly matched the webhook response. This does not remove the separate generation/OOM readiness blocker.

All active production data and Docker volumes were preserved. This audit does not claim production readiness based on service health or HTTP 200.

## Dashboard integration update (2026-09-28)

The operational dashboard is now part of the root Compose stack as `cs-dashboard`, bound only to `127.0.0.1:8090`. Its container reports healthy; `/health/live` and `/health/ready` passed, with the readiness endpoint checking PostgreSQL and Redis. The authenticated system-health endpoint correctly rejects an unauthenticated request (401). Dashboard service health and observed LLM generation status are distinct; unknown generation state is not reported as successful.

The RAG panel now reads counts and measured latencies from database telemetry and returns unavailable values where telemetry is absent. The activity panel has authenticated, filtered execution-list and detail endpoints with allowlisted/redacted telemetry and n8n deep links. Dashboard pool use is threaded, superuser fallback was removed, CORS is allowlisted, and password-change authentication resolves through the auth module. Five focused observability tests pass; Compose configuration and dashboard image build succeeded.

The latest n8n execution visible in the browser was 6195, but the browser explicitly denied access to it. It was not inspected or modified. Historical evidence above remains the last verified live workflow evidence. Workflow export files and WhatsApp source contain the proposed fixes, but they have not been imported/reloaded into their live services. The WhatsApp service was left running to avoid interrupting its current connection. Therefore the dashboard integration is deployed, while end-to-end customer response recovery and current n8n state remain unverified; the system remains **NOT READY**.
