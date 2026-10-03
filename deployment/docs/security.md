# Security notes

No secrets, customer export, workflow credentials or WhatsApp session are bundled. `.env` is generated on target and mode 0600. Local n8n admin remains tunnel-only; DB/cache/model ports remain private. Dashboard CORS in deployment copy has no wildcard origins. Nginx TLS files are operator-provided. Diagnostics are mode 0700 and still require review for PII.

Open findings from repository audit: previous n8n/WhatsApp/session/environment secrets may need rotation if they were ever exposed; the root secret scanner was changed in this task to remove embedded literal credential patterns. Dashboard code and all n8n expressions require Ministry security review. Baileys linked-device operation has operational/account-policy risks. No external penetration test or Ubuntu hardening review was run.

An ignored local `infra/n8n/credentials.json` artifact exists outside this bundle and does not parse as JSON. It was not copied or changed; keep the local file protected and replace it through the approved credential workflow. The bundle contains no credential export.
