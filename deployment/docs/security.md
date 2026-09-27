# Security notes

No secrets, customer export, workflow credentials or WhatsApp session are bundled. `.env` is generated on target and mode 0600. Local n8n admin remains tunnel-only; DB/cache/model ports remain private. Dashboard CORS in deployment copy has no wildcard origins. Nginx TLS files are operator-provided. Diagnostics are mode 0700 and still require review for PII.

Open findings from repository audit: previous n8n/WhatsApp/session/environment secrets may need rotation if they were ever exposed; the root repository contains a secret scanner with literal credential patterns and should be remediated before repository distribution. Dashboard code and all n8n expressions require Ministry security review. Baileys linked-device operation has operational/account-policy risks. No external penetration test or Ubuntu hardening review was run.
