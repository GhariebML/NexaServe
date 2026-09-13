import urllib.request, json, sys

sys.stdout.reconfigure(encoding='utf-8')

API_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxNmFmY2M3My1iYTYwLTQ3YjctOWQzMy0wYjY2YmE5NTY0YmUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiMzcwOGNjYmQtMDAwMy00ZGQzLTk1ZjMtNWFlYmZhNmNiOTE1IiwiaWF0IjoxNzg5MDQ0MDc1LCJleHAiOjE3OTE1OTA0MDB9.gnqmx1Ac4Sw7zsdNiBPL8XkFcm0xhrXMx9848LGlVAc'
BASE = 'http://127.0.0.1:5678/api/v1'

def inspect(eid):
    req = urllib.request.Request(f'{BASE}/executions/{eid}?includeData=true', headers={'X-N8N-API-KEY': API_KEY})
    res = json.loads(urllib.request.urlopen(req).read())
    rd = res.get('data', {}).get('resultData', {}).get('runData', {})
    print(f"=== Execution {eid} (Workflow: {res.get('workflowId')}) ===")
    for node, runs in rd.items():
        print(f"\n--- Node: {node} ---")
        for i, run in enumerate(runs):
            out = run.get('data', {}).get('main', [[]])[0]
            for item in out:
                j = item.get('json', {})
                # Print key summary info
                print("  Keys:", list(j.keys()))
                if 'customer_message' in j:
                    print("  customer_message:", j['customer_message'])
                if 'ai_output' in j:
                    print("  ai_output:", json.dumps(j['ai_output'], ensure_ascii=False))
                if 'reply' in j:
                    print("  reply:", j['reply'])
                if 'response' in j:
                    print("  response:", j['response'][:200])

if __name__ == '__main__':
    eid = sys.argv[1] if len(sys.argv) > 1 else '511'
    inspect(eid)
