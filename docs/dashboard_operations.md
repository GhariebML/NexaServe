# NexaServe Production Dashboard Operations Runbook

**Component:** NexaServe Production Operations & Admin Dashboard  
**Host Port:** `8090` (`http://localhost:8090`)  
**Backend:** FastAPI / Uvicorn Daemon  
**Database:** PostgreSQL 16 (`customerservice` database)  
**Target Audience:** DevOps Engineers, Platform Administrators, Support Tier 2/3  

---

## 1. Starting & Managing Dashboard Service

### Starting the Service
From the repository root:
```powershell
# In PowerShell:
cd e:\NexaServe\dashboard\backend
python -m uvicorn main:app --host 0.0.0.0 --port 8090
```

### Checking Process Status
```powershell
Get-Process -Name "*python*" | Where-Object { $_.CommandLine -like "*uvicorn*" }
```

### Stopping the Service
```powershell
Get-Process -Name "*python*" | Stop-Process -Force
```

---

## 2. Operator Access & Credentials

The dashboard requires JWT bearer authentication for all data operations.

### Seed Accounts:
| Role | Username | Intended Use |
|:---|:---|:---|
| **System Admin** | `admin` | Full unmasked PII view, system audits, all views |
| **Support Agent** | `agent` | Operational ticket handling, masked PII |
| **Auditor / Observer** | `readonly` | High-level metrics view, masked PII, no mutating actions |

> **Security Notice:** Credentials are bootstrapped with cryptographically random passwords  
> and flagged `must_change_password = TRUE`. Passwords are never stored in documentation.  
> On first login each operator is forced to set a new credential.

### Password Rotation Procedure
To update an operator's credentials in PostgreSQL (Argon2id):
```python
from argon2 import PasswordHasher
import psycopg2

ph = PasswordHasher(time_cost=2, memory_cost=65536)
new_hash = ph.hash("NEW_SECURE_PASSWORD")

conn = psycopg2.connect("postgresql://postgres:<DB_PASSWORD>@127.0.0.1:5432/customerservice")
cur = conn.cursor()
cur.execute(
    "UPDATE admin_users SET password_hash = %s, must_change_password = FALSE WHERE username = %s",
    (new_hash, "admin")
)
conn.commit()
conn.close()
```

---

## 3. Operational Troubleshooting

### Issue 1: Dashboard displays "DEGRADED" System Health
- **Check which service is degraded:** Inspect the `/api/dashboard/system-health` endpoint.
- **If Redis is offline:** Ensure `cs-redis` container is up: `docker start cs-redis`
- **If WhatsApp is offline:** Ensure `cs-whatsapp` container is running: `docker start cs-whatsapp`
- **If n8n is offline:** Verify n8n container health: `docker logs cs-n8n --tail 20`

### Issue 2: Customer PII is masked for an Admin
- Verify that the authenticated session token contains `"role": "admin"`.
- If expired, click "Logout" on the bottom sidebar and log in again with the `admin` account.

### Issue 3: High Latency Warning
- Run the index verification query:
```sql
SELECT indexname, tablename FROM pg_indexes WHERE schemaname = 'public';
```
- Ensure `idx_messages_created`, `idx_tickets_created_at`, and `idx_audit_created` exist.

---

## 4. Disaster Recovery & Standalone Verification
To run the automated acceptance test suite at any time:
```powershell
python tests/test_dashboard_production.py
```
Expected output: `Ran 9 tests in ... OK`.
