#!/usr/bin/env python3
"""Publish new n8n workflows and verify webhooks."""
import urllib.request
import json
import time

BASE_URL = "http://localhost:5678/api/v1"
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxNmFmY2M3My1iYTYwLTQ3YjctOWQzMy0wYjY2YmE5NTY0YmUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiMzcwOGNjYmQtMDAwMy00ZGQzLTk1ZjMtNWFlYmZhNmNiOTE1IiwiaWF0IjoxNzg5MDQ0MDc1LCJleHAiOjE3OTE1OTA0MDB9.gnqmx1Ac4Sw7zsdNiBPL8XkFcm0xhrXMx9848LGlVAc"

headers = {
    "X-N8N-API-KEY": API_KEY,
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# Get all workflow IDs from DB
with open("infra/n8n/workflows/07_analytics_reporting.json", "r") as f:
    wf1 = json.load(f)
with open("infra/n8n/workflows/08_csat_survey.json", "r") as f:
    wf2 = json.load(f)
with open("infra/n8n/workflows/09_automation_rules.json", "r") as f:
    wf3 = json.load(f)
with open("infra/n8n/workflows/10_agent_management.json", "r") as f:
    wf4 = json.load(f)
with open("infra/n8n/workflows/11_kb_admin.json", "r") as f:
    wf5 = json.load(f)

workflows = [wf1, wf2, wf3, wf4, wf5]

for wf in workflows:
    wf_id = wf["id"]
    wf_name = wf["name"]
    
    # Publish via API
    payload = {
        "name": wf_name,
        "nodes": wf.get("nodes", []),
        "connections": wf.get("connections", {}),
        "settings": wf.get("settings", {})
    }
    
    try:
        # Use PUT to update (which should publish)
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{BASE_URL}/workflows/{wf_id}",
            data=data,
            headers=headers,
            method="PUT"
        )
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read().decode("utf-8"))
        print(f"Published: {wf_name} ({wf_id})")
    except Exception as e:
        print(f"Error publishing {wf_name}: {e}")

print("\nTrying webhook test after publish...")
time.sleep(3)

for endpoint, data in [
    ("analytics-report", {}),
    ("agent-manage", {"action": "register", "name": "Test Agent", "email": "test@depi.gov.eg"}),
    ("kb-admin", {"action": "search", "query": "depi"}),
]:
    try:
        url = f"http://localhost:5678/webhook/{endpoint}"
        body = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
        resp = urllib.request.urlopen(req, timeout=15)
        result = resp.read().decode("utf-8")[:200]
        print(f"{endpoint}: HTTP {resp.status} - {result}")
    except Exception as e:
        print(f"{endpoint}: ERROR - {e}")

print("\nDone!")
