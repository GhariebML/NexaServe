# Firewall

Host service bindings keep database 5432, Redis 6379 and Ollama 11434 private; administration ports 5678/8080/8090 are loopback-only. If optional proxy is approved, expose TCP 443 only to authorized sources and TCP 80 only for redirect/ACME policy. Restrict QR path through VPN or source allow-list.

Example UFW baseline only after IT confirms SSH source/port: `sudo ufw default deny incoming`; `sudo ufw default allow outgoing`; `sudo ufw allow from <approved-admin-CIDR> to any port <SSH-PORT> proto tcp`; `sudo ufw allow 443/tcp`; `sudo ufw status verbose`. Replace angle-bracket items before execution; validate management access in a second session to avoid lockout. Ministry perimeter firewall remains authoritative.
