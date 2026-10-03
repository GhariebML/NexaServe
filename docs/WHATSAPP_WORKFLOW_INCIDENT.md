# NexaServe WhatsApp Workflow Incident

**Date:** 2026-09-28 (Africa/Cairo)  
**Status:** Root cause identified; gateway guard fixed and deployed. n8n workflow failures remain until the canonical workflow is safely activated and duplicate webhook owners are reviewed.

## Incident and symptom

WhatsApp users reported the literal response `Error in workflow`. A synthetic, non-PII webchat request to `POST /webhook/customer-service` reproduced the n8n failure and returned HTTP 500 with `{"message":"Error in workflow"}`.

## First failing component and evidence

The n8n container log recorded `ReferenceError: isBenefits is not defined`, followed by `Webhook execution failed before a response was sent`. Its stack identifies the n8n JavaScript Code node wrapper and source line 83. The repository has a unique `isBenefits` reference in workflow 04B, node **Program Detector & Query Normalizer**. This identifies the failing code path with high confidence, although the node-level record for execution 6195 could not be opened in the browser and was not retrieved by another means.

Separately, n8n logs show activation failures for `Master - Nexus Customer Service System` (`MASTER_001`) and `NexaServe - Professional Enterprise Master Workflow` (`MASTER_PROFESSIONAL_001`): both attempt to register `customer-service`, a path already owned by another workflow. The repository also contains legacy monolithic Master exports with the same path. These activation collisions can leave the deployed owner ambiguous and prevent intended workflow activation.

## Customer-visible root cause and fix

The Baileys bridge accepted `result.message` as if it were a generated reply and did not require a successful HTTP response. Therefore n8n's generic HTTP 500 body was forwarded verbatim to WhatsApp. The bridge now accepts only `response`, `final_reply`, or `reply` from a successful HTTP response whose workflow status is not `error`/`failed`. Error bodies are not logged; the existing truthful offline response is used instead. The simulation endpoint also reports fallback as `success: false`.

The 04B source export now declares topic matchers at the outer node scope and recognizes Arabic plural forms `المنح`/`منح`, avoiding a missing lexical binding in the runtime node and making scholarship intent match consistently. This export has not been imported into live n8n.

## Configuration and deployment changes

- The deployment Compose file now points at the actual packaged assets under `deployment/assets` and application code under `deployment/application`; it mounts canonical n8n exports at `/opt/nexaserve/workflows` for the documented importer.
- The workflow import script excludes legacy `Master_*` exports, and the publish helper only publishes canonical ingress workflow `CSWF000000000001`.
- WhatsApp container health now requires Baileys `connected: true`, not only an HTTP 200 from the process. Dashboard health also reports a disconnected Baileys session as degraded.
- Existing PostgreSQL volumes, WhatsApp authentication state, and customer rows were not reset or deleted.

## Files changed

- `infra/whatsapp/server.js`, `infra/whatsapp/n8n-response.js`, `infra/whatsapp/Dockerfile`, `docker-compose.yml`
- `infra/n8n/workflows/04B_knowledge_base_faq.json`
- `dashboard/backend/routes.py`, `tests/test_dashboard_runtime_observability.py`
- `scripts/import-workflows.ps1`, `scripts/patch_and_deploy_workflows.py`, `scripts/publish_workflows.py`
- `deployment/compose/docker-compose.yml`, `deployment/application/whatsapp/*`, `deployment/application/dashboard/backend/routes.py`, `deployment/assets/n8n/workflows/04B_knowledge_base_faq.json`
- `tests/test_whatsapp_error_response.mjs`

## Tests and results

- Synthetic webhook reproduction: **FAIL as expected before fix** — HTTP 500, generic n8n error envelope.
- WhatsApp response-envelope tests: **PASS** — only successful reply fields are accepted; generic error messages are rejected.
- 04B Program Detector direct node tests: **PASS** for DEPI scholarship, Digilians eligibility, and ambiguous Arabic input.
- Dashboard observability tests: **PASS**; WhatsApp disconnected state is reported as degraded.
- Root and deployment Compose syntax: **PASS**.
- Live Baileys delivery: **NOT RUN**. Logs included intermittent DNS failures for `web.whatsapp.com`; no approved test recipient was identified.
- Live n8n fix/replay: **NOT RUN**. The browser explicitly denied access to execution 6195. No API/database/UI workaround was used to inspect it or modify live workflows.

## Remaining risks and readiness

The live 04B Code node still fails and the duplicate active webhook owners still require review in n8n. The latest fresh HTTP 500 proves the RAG ingress is still broken. The live WhatsApp-to-delivery path cannot be certified while n8n returns 500 and Baileys connectivity is unstable. The system is **NOT READY** until the canonical workflow is activated without duplicate route owners, a fresh controlled webhook request completes, and one approved WhatsApp test message is received and correlated end to end.
