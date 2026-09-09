# Operations & Troubleshooting Guide
## Customer Service AI Automation System

This guide outlines solutions to common operational scenarios, diagnostic commands, and recovery procedures.

---

## 1. Quick Health Diagnostics

Run the automated health check script from PowerShell:
```powershell
powershell -ExecutionPolicy Bypass -File E:\NexaServe\scripts\healthcheck.ps1
```

Or execute container health inspections manually:
```powershell
docker compose ps
docker compose logs --tail 50 [postgres|n8n|ollama|redis]
```

---

## 2. Common Scenarios & Solutions

### A. Ollama Port Conflict (Port 11434 in use by Host)
- **Symptom**: `Bind for 0.0.0.0:11434 failed: port is already allocated`.
- **Cause**: Windows host already has Ollama running as a background service listening on `127.0.0.1:11434`.
- **Solution**: The Docker environment maps Ollama's host port to `11435` (`127.0.0.1:11435:11434`), while internal containers (n8n) communicate directly with `http://ollama:11434`. Do NOT change the host binding back to 11434 unless the host Ollama process is terminated.

### B. Out of Memory (OOM) or llama-server Process Terminated
- **Symptom**: `ggml_backend_cpu_buffer_type_alloc_buffer: failed to allocate buffer`.
- **Cause**: Host Windows virtual memory is exhausted, or WSL2 RAM has hit its ceiling.
- **Solution**:
  1. Verify free RAM inside Docker: `docker run --rm alpine free -m`.
  2. Use a compact, quantized model such as `llama3.2:3b` (~2.5 GB RAM) instead of larger models (e.g. 8B+ or 14B+).
  3. Ensure no memory leaks in host processes (e.g., excessive Chrome tabs or dead background processes).

### C. Low Disk Space Warning on Drive C:
- **Symptom**: Windows throws "Low Disk Space" notifications; pagefile fails to expand.
- **Verification**: Check logical disk space:
  ```powershell
  Get-CimInstance Win32_LogicalDisk | Select-Object DeviceID, FreeSpace
  ```
- **Rule**: All project data must reside in `E:\NexaServe\data\`. Never run `docker pull` or `ollama pull` directly on the host without setting `OLLAMA_MODELS` to Drive E:.

### D. n8n Cannot Connect to PostgreSQL
- **Symptom**: n8n container exits or loops with `Connection to postgres:5432 failed`.
- **Diagnostics**:
  1. Check PostgreSQL health: `docker exec cs-postgres pg_isready -U postgres`
  2. Inspect PostgreSQL initialization logs: `docker logs cs-postgres`
  3. Verify `init-databases.sh` created the `n8n` database:
     ```powershell
     docker exec cs-postgres psql -U postgres -c "\l"
     ```

### E. Restoring from a Backup
To restore the PostgreSQL cluster and n8n workflows from the latest automated backup:
```powershell
powershell -ExecutionPolicy Bypass -File E:\NexaServe\scripts\restore.ps1
```
Or to restore from a specific timestamped backup directory:
```powershell
powershell -ExecutionPolicy Bypass -File E:\NexaServe\scripts\restore.ps1 -BackupFolder "backup_20260909_013000"
```

---

## 3. Emergency Restart Protocol

If services become unresponsive:
```powershell
# Stop all services gracefully
docker compose down

# Start the stack and stream logs
docker compose up -d
docker compose logs -f --tail 20
```
