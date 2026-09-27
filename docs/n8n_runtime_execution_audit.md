# n8n Runtime Execution Audit

## Evidence set

- Baseline runtime was inspected directly in `execution_entity`, `execution_data`, and `workflow_entity` before edits. It had 38 workflows (17 active), 64 error executions, four crashed executions, and several running executions at the checkpoint.
- Synthetic request `forensic-official-faq-verify-01` ran as master execution 6124; child executions 6125 (session), 6126 (intent), 6127 (04B), 6128 (output), 6129 (logger). The exact trace is in `logs/runtime_forensic/official_faq_trace.json`.
- In execution 6127, the program detector, embedding request, SQL retrieval, formatter, context gate, generation HTTP node, and guardrail all have recorded run entries. Retrieval/context/guardrail succeeded. Qwen’s HTTP request failed after 34.8s because the Ollama model server was killed.
- The customer webhook returned 200 in 36.4s, which concealed the LLM failure because the workflow intentionally falls back to a curated KB answer.

## Node execution from the official FAQ replay

| Node | Status | Latency | Observed result |
|---|---:|---:|---|
| Program Detector & Query Normalizer | success | 7 ms | DEBI filter; not ambiguous |
| Generate Embedding | success | 176 ms | `nomic-embed-text`, 768 dimensions |
| Query Bilingual Knowledge Base | success | 34 ms | Five DEBI rows; official FAQ id 101 ranked first, relevance 56.31 |
| Format RAG Knowledge Response | success | 11 ms | All five records formatted (the earlier version only used the first item) |
| Check if LLM Needed | success | 3 ms | Context contains the exact official FAQ question and answer plus four other FAQ records |
| Qwen RAG Grounded Response | failed internally; continue-on-fail | 34,846 ms | HTTP 500: `llama-server process has terminated: signal: killed` |
| Guardrail & Professional Formatter | success | 34 ms | Returned exact top-record FAQ answer as curated fallback |
| Output dispatcher | success | 86 ms in master path | Webchat payload path; no WhatsApp send tested |
| Conversation logger | success | 434 ms in master path | Saved customer and AI messages; exact final answer matched webhook response |
| Respond to Ingress Webhook | success | 7 ms | HTTP 200, same answer text as logger |

## Failures and skipped branches

- Earlier live 04B used a JSON array as the Ollama `/api/generate` body. The model returned HTTP 400 (`cannot unmarshal array into ... GenerateRequest`). This was changed to a valid JSON object body and loaded into the active n8n version.
- The formatter used `$input.first()` while the Postgres node emits multiple items; four retrieved records were silently dropped. It now maps all input items and includes `source_url`.
- Zero-row SQL retrieval could stop downstream nodes; `alwaysOutputData` now carries the no-context case into a safe deflection path.
- The fixed generation request reaches Ollama, but the process is OOM-killed. `continueOnFail` means n8n shows a successful top-level run even when the generation node failed.
- Intent classifier historically timed out at ~45 seconds (`ECONNABORTED`), then the parser sometimes selected `general_support`. A deterministic FAQ fallback after classifier error was added. It is active, but broad classification quality still needs a non-OOM controlled run.
- Thirty cases were submitted concurrently in a load attempt. Four returned HTTP 200 and 26 returned HTTP 503 `Database is not ready!`. The concurrent run overlapped an earlier serial runner; the JSONL file is therefore not a reliable complete per-request record. Do not use it as a passing test set. Raw file retained; the bounded results are summarized in `response_quality_report.md`.
- After stress, aggregate execution counts showed 73 errors and seven crashes; the baseline was 64 errors/four crashed. Some delta may include ambient live traffic, so it cannot all be attributed to the synthetic requests.
- The first live probe on the final 04B revision caught a duplicate `topicCategory` declaration (execution 6133, HTTP 500). It was removed, the workflow reloaded as version `d3eb1aec-83c5-4c3f-a778-9c4a60a059ee`, and the same clarification probe then passed as master execution 6134 with child 6137. Messages and audit rows matched the exact webhook reply and shared request ID/parent execution ID.
- Latest aggregate table snapshot after this audit: 5,175 success, 75 error, seven crashed, zero running. Error/crash increments may contain synthetic and ambient traffic; no individual production request payloads were included in reports.

## Active versions

Workflow 01, 03, 04B and logger 05 are active; their `versionId` equals `activeVersionId` after the graceful n8n reload. The latest 04B version is `d3eb1aec-83c5-4c3f-a778-9c4a60a059ee`. Webchat verification execution 6134 returned a clarification and logged it with matching request ID and parent execution ID. See [runtime trace](../logs/runtime_forensic/official_faq_trace.json).
