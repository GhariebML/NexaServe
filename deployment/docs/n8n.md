# n8n workflows

Canonical core workflow JSONs are bundled under `assets/n8n/workflows`. They are intentionally inactive and have no credentials. Import with `scripts/deploy_workflows.sh`; create the PostgreSQL credential inside the target n8n UI and assign it to every database node before activation. Verify workflow IDs, called subworkflow IDs, Ollama URLs, and webhook targets against each workflow execution.

n8n uses its dedicated PostgreSQL DB and persistent volume; access its editor via SSH tunnel by default. Public base URL and `WEBHOOK_URL` must match the approved TLS endpoint. Keep encryption key protected. Never import the ignored local credential file.

Canonical workflows set `settings.errorWorkflow` to `CSWF000000000008` (Global Error Handler & Dead Letter Queue). After import, bind the single `Postgres account` credential (database `customerservice`, user `cs_app_user`) to every Postgres node (20 nodes across 8 workflows) before activation; the exports intentionally carry no credentials.
