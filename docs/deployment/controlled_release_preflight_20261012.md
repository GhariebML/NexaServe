# Full controlled release preflight — 2026-10-12

## Decision

**HOLD. No Ministry server write operation was performed.** The updated release brief requires the backup/restore, n8n API, workflow reconciliation, and dashboard visual-review gates to pass before deployment. They do not currently pass. The report and manifest describe a candidate and the verified state; they do not approve the candidate for production.

## Local candidate

- Repository: `E:\NexaServe`
- Branch/commit: `master` / `a0b9a5e3d93673b159dc68b81e3a9bb2eda0516d`
- No release tag points at this commit. `deployment/VERSION` remains `0.1.1`, so there is no distinct immutable release identifier for this candidate.
- Source was clean before this report and manifest were created. They are the only new local artifacts from this preflight; no source or workflow file was changed.
- The dashboard candidate includes reporting and Excel exports, related backend changes, and the sanitized RAG evaluation artifact. Root and packaged dashboard contents match; `index.html` and `Dockerfile` have line-ending-only differences.
- Recent dashboard commits do not change workflow files. The local packaged workflow directory nevertheless differs from the deployed bundle and must not be synchronized by filename or bundle presence alone.

## Local checks already completed

- Reporting/API suite: **25 passed**.
- Deployment runtime-observability suite: **6 passed**.
- JavaScript syntax, Python compilation, `git diff --check`, and Compose config validation: passed. Compose validation reports local `EMBED_MODEL` and `EMBED_DIMENSION` are unset; those are outside the dashboard build.
- Targeted dashboard image build: **passed**, with build context `deployment/application/dashboard`. No local app container was started.
- RAG summary artifact SHA-256: `BACDBF6618C32DE1C3CB3EA3C715A029428F6AA936579F932E747FA40E0BAD55`.
- Current RAG evaluation: **33 passed, 2 failed, 1 blocked, 36 planned**; master verdict `NOT_READY`; runtime identity and corpus version are missing. Do not call 33/36 answer accuracy or describe the system as ready.

## Visual readiness

The brief says an earlier dashboard redesign was unsatisfactory. Repository search found no visual-review or design-approval record. The available local browser preview showed only the login dialog, and the static preview did not serve the stylesheet at the app's `/static/` path. I did not authenticate or bypass the login. Therefore the current interior dashboard design has **not** passed visual review, and its fit to the intended final design is unverified. This is a release blocker under the supplied brief.

## Ministry server state (read-only)

- Strict SSH host-key validation succeeded for alias `nexaserve-ministry`, resolving to the expected `depi@10.179.0.125`; the server reported hostname and account `depi`.
- Active deployment: Compose project `nexaserve`, directory `/opt/nexaserve/deployment`, files `compose/docker-compose.yml` and `compose/docker-compose.gpu.yml`.
- Running containers: PostgreSQL, Redis, Ollama, n8n, WhatsApp, and dashboard; all six reported healthy at inspection.
- Dashboard: container `cs-dashboard`, image `nexaserve-dashboard`, image ID `sha256:dcaf499f19db8627f979ba60ef381641678585f06917ba9d1a278ecf1d19e18b`, created 2026-09-28. OpenAPI reports app version `2.0.0` with 12 paths. `/openapi.json` returned 200; `/health/ready` returned 404 on the currently deployed app.
- n8n: running image tag `2.38.1`; `/healthz` returned 200.
- Database target configured for the dashboard: `customerservice`, application user `cs_app_user`; engine is PostgreSQL. This target was read from the running dashboard container configuration; no authenticated SQL identity check or customer/knowledge-row query was completed.
- Persistent named volumes include `nexaserve_postgres-data`, `nexaserve_redis-data`, `nexaserve_ollama-data`, `nexaserve_n8n-data`, `nexaserve_whatsapp-auth`, and `nexaserve_source-data`. Dashboard has no persistent mount.
- Deployed bundle version is `0.1.1`. The server source checkout is clean at `cd918d9`, different from the local candidate commit. The candidate therefore needs an explicit file manifest and must not be deployed by updating the server checkout wholesale.
- Dashboard and n8n API inspection did not expose secret values. The dashboard container has no `N8N_API_KEY`; a read-only workflow-list request returned HTTP 401. The live n8n workflow inventory and activation states could not be verified.

## Workflow file comparison

The local deployment bundle has 11 JSON files; the deployed mounted bundle has 10. All 10 shared stable IDs have different raw-file SHA-256 values. Their classifications are **conflicting/uncertain** until the live API is available and each difference is reviewed. Actual live activation state is unknown; the `active` properties in bundle files are not proof of current server activation.

| Stable ID | Workflow | Local file | Deployed file | Classification |
|---|---|---|---|---|
| `CSWF000000000008` | Global Error Handler & Dead Letter Queue | `00_global_error_handler.json` | `00_global_error_handler.json` | Conflicting/uncertain |
| `CSWF000000000001` | Customer Service Gateway & Dispatcher | `01_gateway_dispatcher.json` | `01_gateway_dispatcher.json` | Conflicting/uncertain |
| `CSWF000000000002` | Customer Profile & Session Manager | `02_customer_session.json` | `02_customer_session.json` | Conflicting/uncertain |
| `CSWF000000000003` | AI Cognitive & Intent Engine | `03_ai_intent_engine.json` | `03_ai_intent_engine.json` | Conflicting/uncertain |
| `CSWF000000000004` | Order Lookup & Tracking | `04A_order_lookup.json` | `04A_order_lookup.json` | Conflicting/uncertain |
| `CSWF000000000005` | Knowledge Base & FAQ | `04B_knowledge_base_faq.json` | `04B_knowledge_base_faq.json` | Conflicting/uncertain |
| `CSWF000000000006` | Human in the Loop Escalation | `04C_human_escalation.json` | `04C_human_escalation.json` | Conflicting/uncertain |
| `RWLCadRzOPjTHXVo` | Human in the Loop Agent Bridge | `04D_agent_response_bridge.json` | `04D_agent_response_bridge.json` | Conflicting/uncertain |
| `CSWF000000000007` | Conversation & Audit Logger | `05_conversation_logger.json` | `05_conversation_logger.json` | Conflicting/uncertain |
| `F7kjakLJXmzBDsvS` | Output Channel Dispatcher | `06_output_dispatcher.json` | `06_output_dispatcher.json` | Conflicting/uncertain; local ID duplicated |

An additional local file, `06_output_channel_dispatcher.json`, uses the same stable ID `F7kjakLJXmzBDsvS` as local `06_output_dispatcher.json`, but has a different SHA-256 and is absent from the deployed bundle. This duplicate-ID conflict must be resolved before any workflow candidate can be selected. Since the API credential is unavailable, no workflow export or live stable-ID comparison was attempted beyond the mounted bundle.

## Backup and recovery gate

- The server backup directory is mode `0700`, owned by `depi:depi`.
- Existing database dumps, secret-bearing environment copies, and deployment archive are dated 2026-09-28, stored on the server's own filesystem, and are not current off-host recovery evidence.
- The repository's upgrade/backup instructions require a protected off-host backup, integrity checks, and a restore test in an isolated recovery environment. No approved off-host destination, isolated restore target, or accepted recent restore evidence was established.
- No fresh backup, workflow export, archive, database dump, image tag, or server-side file was created in this preflight.

## Proposed manifest

The machine-readable proposed manifest is [controlled_release_manifest_20261012.json](E:/NexaServe/docs/deployment/controlled_release_manifest_20261012.json). It marks dashboard publication and every workflow update as held. If the gates later pass, the proposed service scope is dashboard plus only individually approved n8n workflow IDs. PostgreSQL, Redis, Ollama, WhatsApp, persistent volumes, and knowledge records are excluded from update; no migrations are proposed.

## Remaining gates

1. Establish the Ministry-approved encrypted off-host backup destination and isolated restore target, or validate restore evidence explicitly accepted by the deployment policy.
2. Provision authorized n8n API access through the approved server secret-management process; do not send an API key in chat.
3. Reconcile the duplicate local workflow ID and review all per-ID differences against the live workflow exports. Select the exact workflow IDs and intended activation states.
4. Complete and record visual review of the intended final dashboard design. The present static login screenshot is not such a review.
5. Assign an immutable release identifier and validate the exact selected artifact set.

Until those gates pass, preserve the live release and do not run any remote write operation.

