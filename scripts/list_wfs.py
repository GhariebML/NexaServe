import os
import requests
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("N8N_API_KEY")
print(f"API key present: {bool(key)}")
resp = requests.get("http://localhost:5678/api/v1/workflows", headers={"X-N8N-API-KEY": key})
print("Status code:", resp.status_code)
if resp.status_code == 200:
    data = resp.json().get("data", [])
    print(f"Total workflows: {len(data)}")
    for w in data:
        print(f"ID: {w.get('id')} | Active: {w.get('active')} | Name: {w.get('name')}")
else:
    print(resp.text[:200])
