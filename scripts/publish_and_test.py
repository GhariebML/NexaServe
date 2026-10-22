#!/usr/bin/env python3
"""Explicitly update allowlisted auxiliary workflows; never activate or test webhooks."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import urllib.request

from n8n_release_policy import canonical_workflow_paths

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_WORKFLOWS = {
    "CSWF000000000009": "07_analytics_reporting.json",
    "CSWF000000000010": "08_csat_survey.json",
    "CSWF000000000011": "09_automation_rules.json",
    "CSWF000000000012": "10_agent_management.json",
    "CSWF000000000013": "11_kb_admin.json",
}
BASE_URL = os.environ.get("N8N_URL", "http://localhost:5678/api/v1").rstrip("/")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--update-workflow", action="append", choices=sorted(ALLOWED_WORKFLOWS), required=True)
    args = parser.parse_args()
    if not os.environ.get("N8N_UPDATE_APPROVED"):
        parser.error("set N8N_UPDATE_APPROVED in the approved operator environment")
    if len(args.update_workflow) != len(set(args.update_workflow)):
        parser.error("duplicate workflow IDs are not allowed")
    try:
        canonical_workflow_paths(ROOT)
    except Exception as exc:
        parser.error(f"n8n release gate blocked update ({type(exc).__name__})")
    api_key = os.environ.get("N8N_API_KEY", "")
    if not api_key:
        parser.error("N8N_API_KEY must be provided through the process environment")
    headers = {"X-N8N-API-KEY": api_key, "Content-Type": "application/json", "Accept": "application/json"}

    for workflow_id in args.update_workflow:
        path = ROOT / "infra" / "n8n" / "workflows" / ALLOWED_WORKFLOWS[workflow_id]
        workflow = json.loads(path.read_text(encoding="utf-8"))
        if workflow.get("id") != workflow_id:
            raise SystemExit(f"Workflow ID mismatch in {path.name}; no further updates or tests attempted.")
        if "active" in workflow and not isinstance(workflow["active"], bool):
            raise SystemExit(f"Invalid activation metadata in {path.name}; no updates were attempted.")
        if workflow.get("active") is True:
            raise SystemExit(f"active=true update blocked for {path.name}; complete isolated import acceptance first.")
        payload = {
            "name": workflow["name"],
            "nodes": workflow.get("nodes", []),
            "connections": workflow.get("connections", {}),
            "settings": workflow.get("settings", {}),
        }
        request = urllib.request.Request(
            f"{BASE_URL}/workflows/{workflow_id}",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="PUT",
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                response.read()
        except Exception as exc:
            print(f"Workflow update failed ({type(exc).__name__}); no webhook tests were attempted.", file=sys.stderr)
            return 1

    print("Allowlisted workflow updates completed; no activation endpoint was called.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
