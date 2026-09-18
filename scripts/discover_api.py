#!/usr/bin/env python3
"""Try different n8n API endpoints to publish workflows."""
import urllib.request
import json
import time

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxNmFmY2M3My1iYTYwLTQ3YjctOWQzMy0wYjY2YmE5NTY0YmUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiMzcwOGNjYmQtMDAwMy00ZGQzLTk1ZjMtNWFlYmZhNmNiOTE1IiwiaWF0IjoxNzg5MDQ0MDc1LCJleHAiOjE3OTE1OTA0MDB9.gnqmx1Ac4Sw7zsdNiBPL8XkFcm0xhrXMx9848LGlVAc"

headers = {
    "X-N8N-API-KEY": API_KEY,
    "Content-Type": "application/json",
    "Accept": "application/json"
}

def try_api(path, method="GET", data=None):
    try:
        body = json.dumps(data).encode("utf-8") if data else None
        req = urllib.request.Request(
            f"http://localhost:5678{path}",
            data=body,
            headers=headers,
            method=method
        )
        resp = urllib.request.urlopen(req, timeout=10)
        return resp.status, resp.read().decode("utf-8")[:300]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")[:300]
    except Exception as e:
        return None, str(e)

# Discover available endpoints
print("=== Discovering n8n API ===")
for path in ["/api/v1/workflows", "/api/v1/webhooks", "/api/v1/active-workflows"]:
    status, result = try_api(path)
    print(f"{path} ({method}): {status}")
    if status == 200:
        print(f"  Result: {result[:200]}")

print("\n=== Getting workflow by ID ===")
# Try to get the analytics workflow by its n8n ID
wf_id = "4FyNJ9LFrf1o2Lh4"
for path in [f"/api/v1/workflows/{wf_id}", f"/api/v1/workflows/{wf_id}/activate"]:
    status, result = try_api(path, "GET")
    print(f"{path}: {status}")
    if status == 200:
        print(f"  Result: {result[:200]}")
    elif status == 404:
        print(f"  Not found")

print("\n=== Trying POST to activate ===")
for path in ["/api/v1/workflows/active"]:
    status, result = try_api(path, "GET")
    print(f"{path}: {status}")

print("\n=== Trying activate by ID ===")
for wf_id in ["4FyNJ9LFrf1o2Lh4", "1wWqCpyw9TeIBnQy", "14jJuUgxEa2fIuNp", "m8wU3lJT0uwRcAdK", "iy94N3FsKaAdVvT2"]:
    for path in [f"/api/v1/workflows/{wf_id}"]:
        status, result = try_api(path, "GET")
        print(f"GET {path}: {status} - {result[:100]}")

print("\n=== Trying v2 API ===")
for path in ["/api/v2/workflows", "/api/v2/active"]:
    status, result = try_api(path, "GET")
    print(f"{path}: {status} - {result[:100]}")

print("\nDone")
