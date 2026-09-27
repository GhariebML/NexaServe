import urllib.request, json
import os, sys

API_KEY = os.environ.get("N8N_API_KEY", "")
if not API_KEY:
    print("[ERROR] N8N_API_KEY environment variable required.")
    sys.exit(1)
BASE = os.environ.get("N8N_URL", "http://localhost:5678/api/v1")

headers = {'X-N8N-API-KEY': API_KEY, 'Accept': 'application/json'}

# Get recent executions (any status)
try:
    req = urllib.request.Request(f'{BASE}/executions?limit=5', headers=headers)
    resp = urllib.request.urlopen(req)
    data = json.loads(resp.read())
    for e in data.get('data', []):
        print(f"Execution {e['id']}: status={e.get('status')} finished={e.get('stoppedAt','?')} workflow={e.get('workflowData',{}).get('name','?')}")
except Exception as ex:
    print(f"Error fetching executions: {ex}")

# Try to get a specific failed execution details
try:
    req = urllib.request.Request(f'{BASE}/executions?limit=1', headers=headers)
    resp = urllib.request.urlopen(req)
    data = json.loads(resp.read())
    if data.get('data'):
        eid = data['data'][0]['id']
        req2 = urllib.request.Request(f'{BASE}/executions/{eid}', headers=headers)
        resp2 = urllib.request.urlopen(req2)
        detail = json.loads(resp2.read())
        # Print error details from the execution
        rd = detail.get('data', {}).get('resultData', {})
        if rd.get('error'):
            print(f"\nError in execution {eid}:")
            err = rd['error']
            print(f"  Message: {err.get('message', 'N/A')}")
            print(f"  Node: {err.get('node', {}).get('name', 'N/A')}")
            print(f"  Description: {err.get('description', 'N/A')}")
        for node_name, runs in rd.get('runData', {}).items():
            for run in runs:
                if run.get('error'):
                    print(f"\nNode '{node_name}' error:")
                    print(f"  {run['error'].get('message', 'N/A')}")
except Exception as ex:
    print(f"Error fetching execution detail: {ex}")
