"""Sanitize machine-readable benchmark artifacts for dashboard display."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


MAX_EVALUATION_AGE = timedelta(days=7)


def summarize_latest_rag_evaluation(
    master_path: Path,
    results_path: Path,
    active_runtime_identity: str | None = None,
    active_corpus_version: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Return only verified summary fields; never return benchmark prompts or answers."""
    master = _read_json(master_path)
    artifact = _read_json(results_path)
    if not master or not artifact:
        return {
            "status": "NOT_EVALUATED",
            "reason": "A complete machine-readable RAG evaluation artifact is unavailable.",
            "metric_name": None,
            "metric_definition": None,
            "pass_rate": None,
            "evaluated_cases": 0,
            "planned_cases": 0,
            "passed": 0,
            "failed": 0,
            "blocked": 0,
            "last_evaluated_at": None,
            "runtime_identity": None,
            "corpus_version": None,
            "historical": True,
            "source_artifact": None,
        }

    suite = next(
        (item for item in master.get("suite_results", [])
         if item.get("test") == "Golden RAG Suite"),
        None,
    )
    summary = artifact.get("summary") if isinstance(artifact.get("summary"), dict) else {}
    passed = _nonnegative_int(summary.get("passed"))
    failed = _nonnegative_int(summary.get("failed"))
    blocked = _nonnegative_int(summary.get("blocked"))
    planned = _nonnegative_int(summary.get("total"))
    completed = passed + failed
    consistent = passed + failed + blocked == planned
    timestamp = summary.get("timestamp") or master.get("finished")
    if not isinstance(timestamp, str):
        timestamp = None

    # The checked-in result has no runtime or corpus identity. Even a clean
    # historical result cannot establish quality for the currently configured app.
    linked = bool(
        active_runtime_identity
        and active_corpus_version
        and artifact.get("runtime_identity") == active_runtime_identity
        and artifact.get("corpus_version") == active_corpus_version
    )
    if not suite or planned == 0 or not consistent:
        status = "NOT_EVALUATED"
        reason = "The result artifact has no complete, internally consistent RAG case summary."
    elif not linked:
        status = "BLOCKED"
        reason = "The result is not linked to an identified active runtime and corpus version."
    elif not timestamp:
        status = "BLOCKED"
        reason = "The result has no verifiable evaluation timestamp."
    elif suite.get("status") == "BLOCKED":
        status = "BLOCKED"
        reason = "The RAG evaluation suite was blocked."
    elif suite.get("status") != "PASS":
        status = "NEEDS_IMPROVEMENT"
        reason = "The latest evaluation suite did not pass."
    elif passed + failed > 0 and failed > 0:
        status = "NEEDS_IMPROVEMENT"
        reason = "The latest evaluation contains failed or blocked cases."
    elif blocked > 0:
        status = "BLOCKED"
        reason = "The latest evaluation contains blocked cases."
    elif _is_stale(timestamp, now or datetime.now(timezone.utc)):
        status = "STALE"
        reason = "The runtime-linked evaluation is older than the seven-day freshness window."
    else:
        status = "HEALTHY"
        reason = None

    return {
        "status": status,
        "reason": reason,
        "metric_name": "Acceptance test pass rate (completed cases)",
        "metric_definition": "Passed benchmark cases divided by completed cases (passed + failed); blocked cases are reported separately.",
        "pass_rate": round(passed / completed, 4) if completed else None,
        "evaluated_cases": completed,
        "planned_cases": planned,
        "passed": passed,
        "failed": failed,
        "blocked": blocked,
        "last_evaluated_at": timestamp,
        "runtime_identity": artifact.get("runtime_identity"),
        "corpus_version": artifact.get("corpus_version"),
        "historical": not linked,
        "source_artifact": "tests/golden_test_results.json",
        "master_verdict": master.get("verdict"),
        "time_zone": "Not recorded in source artifact",
    }


def _nonnegative_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 0
    return number if number >= 0 else 0


def _is_stale(timestamp: str, now: datetime) -> bool:
    try:
        evaluated_at = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return True
    if evaluated_at.tzinfo is None:
        return True
    return now.astimezone(timezone.utc) - evaluated_at.astimezone(timezone.utc) > MAX_EVALUATION_AGE
