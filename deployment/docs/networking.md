# Networking

Compose uses one bridge network for internal service communication. PostgreSQL, Redis and Ollama are not published. n8n (5678), WhatsApp (8080), and dashboard (8090) bind to `127.0.0.1` only for SSH-tunnel administration. Optional proxy publishes 80/443.

Allow only approved DNS/NTP, Ministry package mirrors, approved Docker registries, Ollama model registry, and official scrape domains for online mode. Offline operations still need approved internal DNS/NTP and Ministry repositories. Confirm actual egress requirements with IT; do not open broad outbound access by default.
