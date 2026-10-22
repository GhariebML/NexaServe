#!/usr/bin/env python3
"""Update canonical n8n workflows; activation is separate and explicit."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import urllib.request

from n8n_release_policy import canonical_workflow_paths, validate_activation_ids


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE_URL = "http://localhost:5678/api/v1"


def request_json(url: str, headers: dict[str, str], *, method: str = "GET", payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=15) as response:
        body = response.read().decode("utf-8")
    return json.loads(body) if body else {}


def load_exports() -> list[tuple[Path, dict]]:
    paths = canonical_workflow_paths(ROOT)
    exports = [(path, json.loads(path.read_text(encoding="utf-8"))) for path in paths]
    return exports


def run(*, activate_ids: list[str], api_key: str | None = None, base_url: str | None = None) -> int:
    if activate_ids:
        validate_activation_ids(activate_ids)
    exports = load_exports()
    api_key = api_key if api_key is not None else os.environ.get("N8N_API_KEY", "")
    if not api_key:
        raise RuntimeError("N8N_API_KEY must be provided through the process environment")
    base_url = (base_url or os.environ.get("N8N_URL", DEFAULT_BASE_URL)).rstrip("/")
    headers = {
        "X-N8N-API-KEY": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    existing_data = request_json(f"{base_url}/workflows", headers)
    existing = {item["id"]: item for item in existing_data.get("data", [])}
    imported: dict[str, str] = {}
    for path, workflow in exports:
        workflow_id = workflow["id"]
        payload = {
            "name": workflow.get("name"),
            "nodes": workflow.get("nodes", []),
            "connections": workflow.get("connections", {}),
            "settings": workflow.get("settings", {}),
        }
        if workflow_id in existing:
            response = request_json(
                f"{base_url}/workflows/{workflow_id}", headers, method="PUT", payload=payload
            )
            action = "Updated"
        else:
            response = request_json(f"{base_url}/workflows", headers, method="POST", payload=payload)
            action = "Created"
        returned_id = response.get("id", workflow_id)
        if returned_id != workflow_id:
            raise RuntimeError(f"n8n returned a different workflow ID for {path.name}; activation stopped")
        imported[workflow_id] = action
        print(f"{action}: {path.name} ({workflow_id})")

    # No activation call is reachable until every selected import/update succeeded.
    for workflow_id in activate_ids:
        if workflow_id not in imported:
            raise RuntimeError("activation target was not imported in this successful batch")
        request_json(f"{base_url}/workflows/{workflow_id}/activate", headers, method="POST")
        print(f"Activation requested for allowlisted workflow {workflow_id}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--activate-workflow",
        action="append",
        default=[],
        metavar="ID",
        help="explicitly activate an allowlisted workflow after every canonical update succeeds",
    )
    args = parser.parse_args()
    if args.activate_workflow and not os.environ.get("N8N_ACTIVATION_APPROVED"):
        parser.error("set N8N_ACTIVATION_APPROVED before requesting explicit activation")
    try:
        return run(activate_ids=args.activate_workflow)
    except Exception as exc:
        # Never print response bodies or credentials; a failure returns before activation.
        print(f"Workflow update failed ({type(exc).__name__}); no later activation was attempted.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
