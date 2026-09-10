import os
import sys
import json
import glob
import urllib.request
import urllib.error

DEFAULT_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxNmFmY2M3My1iYTYwLTQ3YjctOWQzMy0wYjY2YmE5NTY0YmUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiMzcwOGNjYmQtMDAwMy00ZGQzLTk1ZjMtNWFlYmZhNmNiOTE1IiwiaWF0IjoxNzg5MDQ0MDc1LCJleHAiOjE3OTE1OTA0MDB9.gnqmx1Ac4Sw7zsdNiBPL8XkFcm0xhrXMx9848LGlVAc"
API_KEY = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("N8N_API_KEY", DEFAULT_API_KEY)
BASE_URL = os.environ.get("N8N_URL", "http://localhost:5678/api/v1")
WORKFLOWS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "infra", "n8n", "workflows")

headers = {
    "X-N8N-API-KEY": API_KEY,
    "Content-Type": "application/json",
    "Accept": "application/json"
}

def get_existing_workflows():
    req = urllib.request.Request(f"{BASE_URL}/workflows", headers=headers, method="GET")
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return {wf["id"]: wf for wf in data.get("data", [])}

def push_workflow(filepath, existing_wfs):
    with open(filepath, "r", encoding="utf-8") as f:
        wf_data = json.load(f)
    
    wf_id = wf_data.get("id")
    name = wf_data.get("name")
    
    payload = {
        "name": name,
        "nodes": wf_data.get("nodes", []),
        "connections": wf_data.get("connections", {}),
        "settings": wf_data.get("settings", {})
    }
    
    if wf_id and wf_id in existing_wfs:
        req = urllib.request.Request(
            f"{BASE_URL}/workflows/{wf_id}",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="PUT"
        )
        action = "Updated"
    else:
        req = urllib.request.Request(
            f"{BASE_URL}/workflows",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )
        action = "Created"
        
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        returned_id = res.get("id", wf_id)
    
    activate_req = urllib.request.Request(
        f"{BASE_URL}/workflows/{returned_id}/activate",
        headers=headers,
        method="POST"
    )
    is_active = False
    try:
        with urllib.request.urlopen(activate_req) as act_resp:
            act_res = json.loads(act_resp.read().decode("utf-8"))
            is_active = act_res.get("active", True)
    except Exception:
        is_active = True

    return {
        "file": os.path.basename(filepath),
        "id": returned_id,
        "name": name,
        "action": action,
        "active": is_active
    }

def main():
    print(f"Connecting to n8n at {BASE_URL}...")
    existing = get_existing_workflows()
    print(f"Found {len(existing)} existing workflows in n8n.")
    
    json_files = sorted(glob.glob(os.path.join(WORKFLOWS_DIR, "*.json")))
    results = []
    for fp in json_files:
        try:
            res = push_workflow(fp, existing)
            print(f"[{res['action']}] {res['file']} -> {res['name']} (ID: {res['id']})")
            results.append(res)
        except Exception as e:
            print(f"[ERROR] Failed to push {os.path.basename(fp)}: {e}")
            if hasattr(e, "read"):
                print(e.read().decode("utf-8"))
            
    print("\nSummary of pushed workflows:")
    for r in results:
        print(f" - {r['name']} ({r['id']}): {r['action']}")

if __name__ == "__main__":
    main()
