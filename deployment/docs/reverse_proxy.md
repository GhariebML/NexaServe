# Reverse proxy and TLS

Optional Nginx profile requires a Ministry-issued full certificate chain and private key in `TLS_CERT_DIR`, mounted read-only. The template redirects HTTP to HTTPS, sends webhook paths to n8n, QR/health to WhatsApp, and other requests to dashboard. Configure DNS, TLS, forwarded headers and body/time limits in the approved deployment environment.

The QR path is security sensitive; add Ministry VPN/IP access restrictions at the perimeter before enabling it. n8n editor is not proxied by default; use an SSH tunnel or separately reviewed protected admin route. Test webhook signature/auth, TLS chain and application routing before internet exposure.
