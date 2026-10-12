"""Sanitize machine-readable benchmark artifacts for dashboard display."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any


MAX_EVALUATION_AGE = timedelta(days=7)
SUMMARY_SCHEMA_VERSION = 1


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def build_sanitized_evaluation_artifact(master_path: Path, results_path: Path) -> dict[str, Any]:
    """Build a small dashboard artifact without copying prompts or answers."""
    master = _read_json(master_path)
    result = _read_json(results_path)
    if not master or not result:
        raise ValueError("A complete master run and RAG result artifact are required")
    suite = next(
        (item for item in master.get("suite_results", [])
         if isinstance(item, dict) and item.get("test") == "Golden RAG Suite"),
        None,
    )
    summary = result.get("summary") if isinstance(result.get("summary"), dict) else None
    if not suite or not summary or "Full report saved to:" not in str(suite.get("stdout_tail", "")):
        raise ValueError("The latest run does not contain a RAG suite summary")
    counts = {key: _nonnegative_int(summary.get(key)) for key in ("total", "passed", "failed", "blocked")}
    if counts["total"] == 0 or counts["passed"] + counts["failed"] + counts["blocked"] != counts["total"]:
        raise ValueError("The RAG suite summary has incomplete or inconsistent case counts")
    results_time = summary.get("timestamp") or master.get("finished")
    if not isinstance(results_time, str) or not _matches_master_run(results_time, master.get("finished")):
        raise ValueError("The RAG result timestamp does not match the latest master test run")

    # Keep only named aggregate fields and identity metadata that the evaluator
    # explicitly recorded. Never copy the source results array.
    payload = {
        "source_artifact": "tests/golden_test_results.json",
        "source_artifact_sha256": _sha256(results_path),
        "master_artifact_sha256": _sha256(master_path),
        "master_finished": master.get("finished"),
        "master_verdict": master.get("verdict"),
        "suite_status": suite.get("status"),
        "summary": {
            **counts,
            "timestamp": results_time,
        },
        "runtime_identity": result.get("runtime_identity"),
        "corpus_version": result.get("corpus_version"),
        "time_zone": "Not recorded in source artifact" if _has_no_timezone(results_time) else None,
    }
    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evaluation": payload,
    }


def summarize_latest_rag_evaluation(
    master_path: Path,
    results_path: Path,
    active_runtime_identity: str | None = None,
    active_corpus_version: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Direct-source helper retained for isolated tests and review tooling."""
    try:
        artifact = build_sanitized_evaluation_artifact(master_path, results_path)
    except ValueError:
        return _not_evaluated("The latest run has no complete, consistent RAG evaluation summary.")
    return summarize_sanitized_evaluation(
        artifact,
        active_runtime_identity=active_runtime_identity,
        active_corpus_version=active_corpus_version,
        now=now,
    )


def summarize_sanitized_evaluation(
    artifact: dict[str, Any] | None,
    active_runtime_identity: str | None = None,
    active_corpus_version: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Validate and summarize the packaged, PII-free benchmark artifact."""
    if not isinstance(artifact, dict) or artifact.get("schema_version") != SUMMARY_SCHEMA_VERSION:
        return _not_evaluated("A supported, sanitized RAG evaluation summary is unavailable.")
    payload = artifact.get("evaluation")
    if not isinstance(payload, dict):
        return _not_evaluated("The sanitized RAG evaluation summary is incomplete.")
    if not all(_valid_sha256(payload.get(key)) for key in ("source_artifact_sha256", "master_artifact_sha256")):
        return _not_evaluated("The sanitized RAG evaluation summary has invalid source checksums.")

    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    planned = _nonnegative_int(summary.get("total"))
    passed = _nonnegative_int(summary.get("passed"))
    failed = _nonnegative_int(summary.get("failed"))
    blocked = _nonnegative_int(summary.get("blocked"))
    completed = passed + failed
    timestamp = summary.get("timestamp")
    suite_status = payload.get("suite_status")
    consistent = planned > 0 and passed + failed + blocked == planned
    timestamp_matches = _matches_master_run(timestamp, payload.get("master_finished"))
    if not consistent or not timestamp_matches:
        return _not_evaluated("The sanitized summary is inconsistent or does not match its recorded test run.")

    linked = bool(
        active_runtime_identity
        and active_corpus_version
        and payload.get("runtime_identity") == active_runtime_identity
        and payload.get("corpus_version") == active_corpus_version
    )
    if not linked:
        status = "BLOCKED"
        reason = "The result is not linked to an identified active runtime and corpus version."
    elif suite_status == "BLOCKED":
        status = "BLOCKED"
        reason = "The RAG evaluation suite was blocked."
    elif suite_status != "PASS":
        status = "NEEDS_IMPROVEMENT"
        reason = "The latest evaluation suite did not pass."
    elif failed > 0:
        status = "NEEDS_IMPROVEMENT"
        reason = "The latest evaluation contains failed cases."
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
        "runtime_identity": payload.get("runtime_identity"),
        "corpus_version": payload.get("corpus_version"),
        "historical": not linked,
        "source_artifact": payload.get("source_artifact"),
        "source_artifact_sha256": payload.get("source_artifact_sha256"),
        "master_verdict": payload.get("master_verdict"),
        "time_zone": payload.get("time_zone"),
    }


def summarize_stored_rag_evaluation(
    summary_path: Path,
    active_runtime_identity: str | None = None,
    active_corpus_version: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Read the packaged summary without needing benchmark results in the image."""
    return summarize_sanitized_evaluation(
        _read_json(summary_path), active_runtime_identity, active_corpus_version, now
    )


def _not_evaluated(reason: str) -> dict[str, Any]:
    return {
        "status": "NOT_EVALUATED", "reason": reason,
        "metric_name": None, "metric_definition": None, "pass_rate": None,
        "evaluated_cases": 0, "planned_cases": 0, "passed": 0, "failed": 0,
        "blocked": 0, "last_evaluated_at": None, "runtime_identity": None,
        "corpus_version": None, "historical": True, "source_artifact": None,
    }


def _nonnegative_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 0
    return number if number >= 0 else 0


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _valid_sha256(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _has_no_timezone(timestamp: str) -> bool:
    try:
        return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).tzinfo is None
    except ValueError:
        return True


def _is_stale(timestamp: str, now: datetime) -> bool:
    try:
        evaluated_at = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return True
    if evaluated_at.tzinfo is None:
        return True
    return now.astimezone(timezone.utc) - evaluated_at.astimezone(timezone.utc) > MAX_EVALUATION_AGE


def _matches_master_run(evaluation_time: Any, run_finished: Any) -> bool:
    if not isinstance(evaluation_time, str) or not isinstance(run_finished, str):
        return False
    try:
        evaluated = datetime.fromisoformat(evaluation_time.replace("Z", "+00:00"))
        finished = datetime.fromisoformat(run_finished.replace("Z", "+00:00"))
        if (evaluated.tzinfo is None) != (finished.tzinfo is None):
            return False
        return abs(finished - evaluated) <= timedelta(minutes=5)
    except ValueError:
        return False
