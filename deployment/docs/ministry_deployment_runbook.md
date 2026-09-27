# Ministry deployment handoff runbook

## Ministry IT must supply

- [ ] Ubuntu 24.04 x86_64 server inventory: CPU/RAM/disk, GPU make/model/VRAM, driver source/version, firmware and reboot window.
- [ ] SSH identities/MFA/break-glass, sudo policy, ownership/group and admin contact.
- [ ] DNS/FQDN, NTP, approved ingress/egress CIDRs, ports, proxies, registries, apt mirror and source-site allowlist.
- [ ] TLS certificate chain/private-key delivery, renewal owner and Nginx exposure approval.
- [ ] Secret vault and recovery procedure for `.env` including n8n encryption key; no secrets by email or ticket.
- [ ] WhatsApp account/device owner, approved test number/phone, linked-device policy and operational support process.
- [ ] Official Digilians FAQ/source documents with approver, source URL/license, effective date and content owner.
- [ ] Backup destination, encryption, retention, RPO/RTO and restore-drill host.
- [ ] Monitoring/alert contacts, incident severity mapping, maintenance/change window and support escalation.

## Operator handoff sequence

1. Record received bundle `VERSION`, checksum result, source commit/build date and approvers.
2. Confirm target host prerequisites and GPU Docker validation; attach redacted outputs.
3. Generate fresh target secrets in approved vault/workstation flow; protect `.env`; verify n8n owner and dashboard administrator are unique.
4. Deploy with `../DEPLOYMENT.md`; retain volumes and logs.
5. Validate schema/migrations, models, actual Arabic generation, correct DEPI retrieval/source/context, no-answer/security handling, all workflow nodes, dashboard/RBAC, HITL and controlled WhatsApp outbound delivery.
6. Verify backup and isolated restore. Confirm logs link request, conversation, execution, RAG/model and exact delivered answer without excess PII.
7. Review all known risks: local audit found generation OOM, failed concurrent webchat requests, Digilians provenance gap, no WhatsApp E2E, and no Ubuntu target verification.
8. Sign acceptance with platform owner, data/knowledge owner, security, network, operations, and Ministry service owner. If any P0 or unchecked criterion remains, do not open customer traffic.

## Ongoing ownership

Assign primary/secondary incident responders, backup/restore owner, official content approver, n8n workflow owner, WhatsApp device custodian and image/model patch owner. Record maintenance windows and secure credential rotation after any exposure or staff/contractor change.
