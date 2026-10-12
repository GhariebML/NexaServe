"""Package a PII-free RAG evaluation summary for dashboard containers."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "dashboard" / "backend"))

from evaluation_summary import build_sanitized_evaluation_artifact  # noqa: E402


def _default_master() -> Path:
    for name in ("FINAL_TEST_RESULTS.json", "final_test_results.json"):
        candidate = ROOT / "tests" / name
        if candidate.exists():
            return candidate
    return ROOT / "tests" / "FINAL_TEST_RESULTS.json"


def _write_atomic(path: Path, artifact: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp_path.replace(path)


def build(master: Path, results: Path, destinations: list[Path]) -> dict:
    artifact = build_sanitized_evaluation_artifact(master, results)
    for destination in destinations:
        _write_atomic(destination, artifact)
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--master", type=Path, default=_default_master())
    parser.add_argument("--results", type=Path, default=ROOT / "tests" / "golden_test_results.json")
    parser.add_argument("--output", type=Path, action="append", help="Output path; may be specified more than once")
    args = parser.parse_args()
    destinations = args.output or [
        ROOT / "dashboard" / "data" / "rag_evaluation_summary.json",
        ROOT / "deployment" / "application" / "dashboard" / "data" / "rag_evaluation_summary.json",
    ]
    try:
        artifact = build(args.master, args.results, destinations)
    except (OSError, ValueError) as exc:
        print(f"Dashboard RAG summary was not updated: {type(exc).__name__}", file=sys.stderr)
        return 1
    summary = artifact["evaluation"]["summary"]
    print(
        "Sanitized dashboard RAG summary written: "
        f"{summary['passed']} passed, {summary['failed']} failed, "
        f"{summary['blocked']} blocked of {summary['total']} planned cases."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
