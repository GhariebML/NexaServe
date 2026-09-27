# Redis

Redis 7 runs on the private Docker bridge with password authentication and a persistent volume. Its Compose health check uses the configured password without printing it. The dashboard checks Redis using `REDIS_HOST=redis`; no host port is published.

Redis is auxiliary; PostgreSQL is the system of record. Check `docker compose logs redis`, `docker compose exec redis redis-cli` with a secure auth method, and health status. Never disable the password or expose port 6379 publicly.
