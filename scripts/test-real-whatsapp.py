# -*- coding: utf-8 -*-
"""
NexaServe Customer Service AI - Real WhatsApp Live Test & Verification Utility
"""

import urllib.request
import urllib.error
import json
import sys
import time

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BRIDGE_STATUS_URL = "http://localhost:8080/status"
BRIDGE_SEND_URL = "http://localhost:8080/send"
GATEWAY_URL = "http://localhost:5678/webhook/customer-service"

BRIDGE_SIMULATE_URL = "http://localhost:8080/simulate"

def get_bridge_status():
    try:
        req = urllib.request.Request(BRIDGE_STATUS_URL, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"status": "OFFLINE", "error": str(e)}

def test_bridge_direct_simulation(customer_phone, customer_name, message_text):
    print(f"\n[Test] Direct WhatsApp Bridge Ingress Simulation...")
    print(f"       From: {customer_name} ({customer_phone})")
    print(f"       Message: \"{message_text}\"")

    payload = {
        "channel": "whatsapp",
        "customer_message": message_text,
        "phone_number": customer_phone,
        "full_name": customer_name,
        "from": customer_phone.replace("+", "")
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            BRIDGE_SIMULATE_URL,
            data=data,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST"
        )
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=15) as resp:
            latency = int((time.time() - t0) * 1000)
            res = json.loads(resp.read().decode("utf-8"))
            print(f"\n[+] AI Live Reply Generated (Latency: {latency}ms):")
            print(f"    - Source:   {res.get('source')}")
            print(f"    - Success:  {res.get('success')}")
            print(f"    - Response:\n\n{res.get('reply')}\n")
            return res
    except Exception as e:
        print(f"[-] Simulation failed: {e}")
        return None

def main():
    print("=" * 70)
    print(" 📱 NexaServe AI - WhatsApp Live Channel Status & Test Utility")
    print("=" * 70)

    st = get_bridge_status()
    print(f"WhatsApp Bridge Status: {st.get('status')}")

    if st.get("status") == "CONNECTED":
        print(f"  -> Connected Phone: +{st.get('phone')}")
        print(f"  -> Account Name:    {st.get('name')}")
        print("  -> Status: Ready for bidirectional live messaging!")
    elif st.get("status") == "QR_READY":
        print("  -> QR code is waiting to be scanned!")
        print("  -> Open in browser: http://localhost:8080/qr")
    else:
        print(f"  -> Bridge is currently {st.get('status')}.")
        print("  -> Launch it via: powershell scripts/connect-whatsapp.ps1")

    # Run real case 1: Arabic FAQ
    print("\n" + "-" * 70)
    print("Real Case 1: Citizen Inquiring about DEPI / Future Skills (Arabic FAQ)")
    print("-" * 70)
    test_bridge_direct_simulation(
        customer_phone="+966509988776",
        customer_name="فهد الشمري",
        message_text="السلام عليكم، ما هي شروط التقديم في مبادرة الرواد الرقميون؟"
    )

    # Run real case 2: Citizen Order Tracking
    print("-" * 70)
    print("Real Case 2: Citizen Inquiring about Service Status (SRV-1001)")
    print("-" * 70)
    test_bridge_direct_simulation(
        customer_phone="+966509988776",
        customer_name="فهد الشمري",
        message_text="أهلاً، أريد معرفة حالة طلبي رقم SRV-1001"
    )

    # Run real case 3: Human Escalation
    print("-" * 70)
    print("Real Case 3: Citizen Escalation with Priority Ticket")
    print("-" * 70)
    test_bridge_direct_simulation(
        customer_phone="+966509988776",
        customer_name="فهد الشمري",
        message_text="لدي مشكلة تقنية معقدة في الخدمة وأحتاج التحدث مع موظف مختص"
    )

if __name__ == "__main__":
    main()
