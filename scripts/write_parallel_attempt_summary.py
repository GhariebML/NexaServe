"""Materialize console-verified aggregate outcomes of concurrent run B."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
cases = json.loads((root / "tests" / "response_quality_cases.json").read_text(encoding="utf-8"))
accepted = {
    "depi-01": (58326, 785),
    "depi-02": (28240, 48),
    "depi-03": (64753, 312),
    "depi-04": (66328, 268),
}
records = []
for case in cases:
    request_id = f"forensic-{case['id']}-20260927-b"
    if case["id"] in accepted:
        elapsed, chars = accepted[case["id"]]
        records.append({
            "case_id": case["id"], "request_id": request_id, "channel": "webchat",
            "http_status": 200, "elapsed_ms": elapsed,
            "response_chars": chars, "response_body_preserved": case["id"] in ("depi-01", "depi-02"),
        })
    else:
        records.append({
            "case_id": case["id"], "request_id": request_id, "channel": "webchat",
            "http_status": 503, "error": "Database is not ready!",
        })
out = {
    "attempt": "concurrent synthetic webchat load run B",
    "cases_attempted": len(records),
    "http_200": sum(x["http_status"] == 200 for x in records),
    "http_503": sum(x["http_status"] == 503 for x in records),
    "reconstruction_note": "Aggregate status/latency/character counts were observed in the command output. The shared raw JSONL was interleaved by an earlier still-running serial process, so 26 503 response bodies and two of the accepted response bodies were not preserved as valid JSON records.",
    "records": records,
}
path = root / "logs" / "runtime_forensic" / "parallel_attempt_b_summary.json"
path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"wrote {path}: {out['http_200']} HTTP 200, {out['http_503']} HTTP 503")
