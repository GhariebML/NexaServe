# -*- coding: utf-8 -*-
import urllib.request
import json
import time
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

prompt = """أنت محرك تصنيف النوايا (Intent Classifier) لمنصة خدمة عملاء مبادرة الرواد الرقميون (DEPI).
صنف رسالة العميل إلى إحدى النوايا التالية بدقة:
1. faq_query: أي سؤال أو استفسار عن مبادرة الرواد الرقميون (DEPI)، الشروط، السن، المؤهلات، المسارات، التخصصات، التسجيل، الامتحانات، SEB، الشهادات، الإقامة، المزايا.
2. order_lookup: الاستعلام عن رقم طلب أو خدمة (مثل: SRV-1001، ORD-1001، تتبع، شحنة).
3. human_escalation: الشكاوى، الغضب، أو طلب التحدث مع موظف/إنسان.
4. general_support: التحيات والترحيب (السلام عليكم، مرحبا، شكرا).

أجب بصيغة JSON فقط:
{"intent": "faq_query"|"order_lookup"|"human_escalation"|"general_support", "confidence": 0.95, "entities": {}, "sentiment": "positive"|"neutral"|"frustrated", "requires_human": false, "direct_response": ""}

رسالة العميل: "ما هي شروط التقديم في مبادرة الرواد الرقميون؟"
"""

body = {
    "model": "qwen2.5:3b",
    "prompt": prompt,
    "stream": False,
    "format": "json",
    "options": {
        "num_ctx": 1024,
        "num_predict": 100,
        "temperature": 0.1
    }
}

t0 = time.time()
req = urllib.request.Request("http://localhost:11434/api/generate", data=json.dumps(body).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        t1 = time.time()
        print(f"Time taken: {t1 - t0:.2f}s")
        print("Response:", res.get("response"))
except Exception as e:
    print("Error:", e)
