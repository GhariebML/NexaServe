# WhatsApp bridge

The repository service is a Node 20 Alpine Baileys bridge; the deployment persists auth in a private Docker named volume and calls n8n over its internal network. The QR endpoint binds to host loopback unless the optional proxy is enabled.

Use a Ministry-approved test handset. Pair only on a VPN/admin network, restrict `/qr`, and verify actual inbound and outbound text with request/execution/message correlation. Health endpoint and `CONNECTED` state alone do not prove delivery. Never include auth state in an archive or diagnostics.
