import urllib.request, json, sys

sys.stdout.reconfigure(encoding='utf-8')

url = "http://127.0.0.1:11434/api/generate"
payload = {
    "model": "qwen2.5:1.5b",
    "prompt": """أنت المساعد الذكي الرسمي لمبادرة الرواد الرقميون (DEPI).
أجب بصيغة JSON فقط متضمناً intent و direct_response:
{"intent": "general_support", "direct_response": "..."}

سؤال العميل: ما هي شروط التقديم في مبادرة الرواد الرقميون؟""",
    "format": "json",
    "stream": False,
    "options": {
        "num_ctx": 2048,
        "temperature": 0.2
    }
}

try:
    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=60) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        print("Model:", res.get("model"))
        print("Response:\n", res.get("response"))
except Exception as e:
    print("Error:", e)
