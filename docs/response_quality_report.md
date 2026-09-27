# Response Quality Report

## Method

`tests/response_quality_cases.json` contains 30 planned synthetic requests covering DEPI, Digilians, ambiguous wording, comparison, English, no-answer, prompt injection, FAQ exact/paraphrase, official scraped fact, out-of-scope, and memory follow-up. Requests used `channel=webchat`; no real WhatsApp messages were sent.

## Results

- A serialized attempt was started; it took tens of seconds per request and destabilized the active runtime. Its raw output was overlapped by a concurrent load attempt and is retained at `logs/runtime_forensic/controlled_replays.jsonl`; that file is not a reliable one-record-per-case ledger.
- The separate 30-case concurrent load attempt completed: **4/30 HTTP 200, 26/30 HTTP 503** with body `Database is not ready!`. The four accepted cases were DEPI 1–4; Qwen generation process was killed by memory pressure. These are failed capacity/quality tests, not passing responses.
- Of accepted responses, `ما هي المنح المتاحة في DEPI؟` returned “المدة التدريبية للبرنامج هي أربعة أشهر بحد أقصى.” That answer is about duration, not available scholarships: **relevance fail**.
- An exact official scraped FAQ replay returned its precise source answer, but Qwen failed and the guardrail used a curated fallback. This passes fact/source agreement, but does not pass the LLM-grounding criterion.
- A synthetic ambiguous request returned an Arabic clarification, and both message rows plus audit log matched the exact HTTP response after correlation patch.

## Post-fix retrieval-stage checks

The active 04B SQL/filter/format logic was replayed for all 30 query cases plus one dedicated source query. Topic-aware ranking selected the expected conditions, benefits, tracks, and online-training records; no opposite-program record entered DEBI/Digilians top 10; ambiguous prompts remained separate; no-answer, prompt-injection, and out-of-scope cases failed the new evidence gate. These are retrieval-stage checks only. They do not convert the earlier 26/30 HTTP 503 load failure into a successful end-to-end suite.

The dedicated source traceability pytest run ended **2 passed, 1 failed**. The failing test requires a successful Qwen-generated answer; the recorded response was a curated fallback because the Ollama llama-server was killed.

## Rubric and acceptance status

| Criterion | Current finding |
|---|---|
| Correct program | 04B filters DEBI correctly in the official DEPI trace; a complete 30-case cross-program evaluation was blocked. |
| Correct facts / grounded | Official FAQ fallback exact; model-generated answer not verified because Qwen process failed. |
| Relevant | Fail: scholarship question answered with duration in accepted set. |
| Complete | Not established across requested categories. |
| Language | Arabic direct response observed; bilingual quality not established. |
| No hallucination / no-answer | Security and no-answer cases were not reliably evaluated under 503/OOM conditions. |
| No internal metadata | No context labels leaked in accepted final sample, but internal `[DEBI]`/question-answer labels are present in LLM context. |
| No cross-program leakage | DEBI sample filter correctly excluded DIGILIANS. Full 0% rate not established. |
| Professional tone | Mixed; no complete evaluation. |

The accepted traffic sample is insufficient for customer-quality signoff. There is no score inflation or criteria change.
