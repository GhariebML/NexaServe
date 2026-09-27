# PostgreSQL data layer

The repository schema creates `customers`, `conversations`, `messages`, `orders`, `knowledge_base`, `tickets`, `audit_logs`, `customer_memory`, and `conversation_summaries`. PostgreSQL is `pgvector/pgvector` on major 16; `customerservice` and a separate n8n DB use dedicated roles. Fresh-volume bootstrap applies schema plus additive professional-support/admin migrations and grants application permissions. It does not seed synthetic customers or reset existing data.

For existing databases, verified backup first; then `scripts/migrate.sh`. Validate extensions, tables, migration ledger and grants. Fresh init scripts only run when Postgres data volume is empty. Never delete volumes or apply `DROP` cleanup as a recovery step.
