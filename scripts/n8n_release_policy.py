"""Shared offline policy for selecting and validating canonical n8n exports."""

from __future__ import annotations

import json
from pathlib import Path


ACTIVATABLE_WORKFLOW_IDS = frozenset({"CSWF000000000001"})


def canonical_workflow_paths(root: Path, *, reject_active: bool = True) -> list[Path]:
    inventory_path = root / "deployment" / "inventory.json"
    source_dir = root / "infra" / "n8n" / "workflows"
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    if not isinstance(inventory, dict):
        raise ValueError("deployment inventory must be a JSON object")
    rows = inventory.get("workflows")
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError("deployment inventory has an invalid workflow list")
    workflow_meta = inventory.get("n8n_workflows", {})
    acceptance = workflow_meta.get("import_acceptance") if isinstance(workflow_meta, dict) else None
    if not isinstance(acceptance, dict) or acceptance.get("status") != "passed" or not acceptance.get("n8n_version") or not acceptance.get("evidence"):
        raise ValueError("isolated target-like import acceptance evidence is not recorded")
    names = [row.get("file") for row in rows]
    expected_ids = {row.get("file"): row.get("id") for row in rows}
    if not names or any(not isinstance(name, str) or not name.endswith(".json") for name in names):
        raise ValueError("deployment inventory has an invalid workflow file list")
    if len(names) != len(set(names)):
        raise ValueError("deployment inventory repeats workflow filenames")

    paths = [source_dir / name for name in names]
    seen_ids: set[str] = set()
    for path in paths:
        workflow = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(workflow, dict):
            raise ValueError(f"workflow metadata is not an object: {path.name}")
        workflow_id = workflow.get("id")
        if not isinstance(workflow_id, str) or not workflow_id.strip():
            raise ValueError(f"workflow has no stable ID: {path.name}")
        if workflow_id in seen_ids:
            raise ValueError(f"canonical source repeats workflow ID: {workflow_id}")
        seen_ids.add(workflow_id)
        if workflow_id != expected_ids[path.name]:
            raise ValueError(f"inventory ID mismatch: {path.name}")
        if "active" in workflow and not isinstance(workflow["active"], bool):
            raise ValueError(f"invalid active metadata type: {path.name}")
        if reject_active and workflow.get("active") is True:
            raise ValueError(f"active=true export is blocked pending import acceptance: {path.name}")

    return paths


def validate_activation_ids(workflow_ids: list[str]) -> None:
    if not workflow_ids:
        raise ValueError("at least one explicit --activate-workflow ID is required")
    if len(workflow_ids) != len(set(workflow_ids)):
        raise ValueError("activation allowlist contains duplicate IDs")
    unknown = sorted(set(workflow_ids) - ACTIVATABLE_WORKFLOW_IDS)
    if unknown:
        raise ValueError("activation requested for a workflow outside the allowlist")
