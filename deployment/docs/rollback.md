# Rollback

Stop external ingress first. Preserve current logs, images, DB and volumes. Reapply the previous reviewed bundle and images; restore the pre-change database backup only in a controlled recovery plan if schema compatibility requires it. Validate before traffic resumes.

`scripts/rollback.sh /path/to/previous/deployment` is intentionally non-destructive and prints the sequence; it does not run SQL rollback, switch volumes, or delete anything. Do not run `docker compose down -v`, `docker system prune --volumes`, or improvised destructive database statements.
