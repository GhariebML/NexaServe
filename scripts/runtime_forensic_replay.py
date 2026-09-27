"""Synthetic webchat replay; never sends messages through the WhatsApp channel."""
import json
import time
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "tests" / "response_quality_cases.json"
URL = "http://127.0.0.1:5678/webhook/customer-service"

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--concurrency", type=int, default=1, help="Use 1 for sequential production-safe measurement.")
args = parser.parse_args()
if args.concurrency < 1 or args.concurrency > 3:
    raise SystemExit("--concurrency must be between 1 and 3")
run_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
OUT = ROOT / "logs" / "runtime_forensic" / f"controlled_replays_{run_stamp}.jsonl"

OUT.parent.mkdir(parents=True, exist_ok=True)
with CASES.open(encoding="utf-8") as f:
    cases = json.load(f)

def run_case(case):
    request_id = f"forensic-{case['id']}-{run_stamp}"
    payload = {
            "request_id": request_id,
            "channel_user_id": request_id,
            "channel": "webchat",
            "full_name": "Synthetic Forensic Test",
            "locale": case["language"],
            "customer_message": case["query"],
        }
    started = time.monotonic()
    try:
        response = requests.post(URL, json=payload, timeout=120)
        elapsed_ms = round((time.monotonic() - started) * 1000)
        try:
            body = response.json()
        except ValueError:
            body = {"raw_body": response.text[:2000]}
        record = {
                "case": case,
                "request_id": request_id,
                "channel": "webchat",
                "http_status": response.status_code,
                "elapsed_ms": elapsed_ms,
                "response": body,
        }
    except Exception as exc:
        record = {
                "case": case,
                "request_id": request_id,
                "channel": "webchat",
                "elapsed_ms": round((time.monotonic() - started) * 1000),
                "error": f"{type(exc).__name__}: {exc}",
        }
    return record

records = []
with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
    futures = [pool.submit(run_case, case) for case in cases]
    for future in as_completed(futures):
        record = future.result()
        records.append(record)
        response = record.get("response", {})
        answer = response.get("response", response.get("reply", response.get("direct_reply", ""))) if isinstance(response, dict) else ""
        print(json.dumps({
            "case": record["case"]["id"], "http": record.get("http_status"),
            "ms": record["elapsed_ms"], "intent": response.get("intent"),
            "response_chars": len(answer or ""), "error": record.get("error")
        }, ensure_ascii=False), flush=True)
with OUT.open("w", encoding="utf-8") as out:
    for record in records:
        out.write(json.dumps(record, ensure_ascii=False) + "\n")
print(f"saved={OUT} cases={len(cases)}")
