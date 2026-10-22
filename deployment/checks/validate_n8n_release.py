#!/usr/bin/env python3
"""Fail-closed, offline validation for canonical n8n release metadata."""

from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "deployment" / "assets" / "n8n" / "workflows"
SOURCE = ROOT / "infra" / "n8n" / "workflows"
DISPATCHER_ID = "F7kjakLJXmzBDsvS"
ERROR_HANDLER_ID = "CSWF000000000008"


def validate_release(root: Path = ROOT) -> list[str]:
    package = root / "deployment" / "assets" / "n8n" / "workflows"
    source = root / "infra" / "n8n" / "workflows"
    inventory_path = root / "deployment" / "inventory.json"
    errors: list[str] = []
    try:
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        rows = inventory["workflows"]
    except (OSError, ValueError, KeyError, TypeError):
        return ["deployment/inventory.json is invalid or unreadable"]

    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        return ["inventory workflow list is invalid"]
    names = [row.get("file") for row in rows]
    if not names or any(not isinstance(name, str) or not name.endswith(".json") for name in names):
        return ["inventory workflow file list is invalid"]
    if len(names) != len(set(names)):
        errors.append("inventory repeats a workflow filename")

    expected_names = set(names)
    package_metadata = inventory.get("n8n_workflows", {})
    if not isinstance(package_metadata, dict):
        errors.append("inventory n8n_workflows metadata is invalid")
        package_metadata = {}
    if package_metadata.get("canonical_exports") != len(expected_names):
        errors.append("inventory canonical_exports count disagrees with workflow list")
    if package_metadata.get("credentials_included") is not False:
        errors.append("inventory must state that credential definitions are excluded")
    acceptance = package_metadata.get("import_acceptance")
    if not isinstance(acceptance, dict) or acceptance.get("status") != "passed" or not acceptance.get("n8n_version") or not acceptance.get("evidence"):
        errors.append("isolated target-like n8n import acceptance evidence is not recorded")
    actual_names = {path.name for path in package.glob("*.json")}
    if actual_names != expected_names:
        errors.append("packaged workflow filenames do not match inventory")

    by_id: dict[str, list[str]] = {}
    source_by_id: dict[str, list[str]] = {}
    parsed: dict[str, dict] = {}
    active_true_names: set[str] = set()
    for name in sorted(expected_names):
        for directory, index in ((package, by_id), (source, source_by_id)):
            path = directory / name
            try:
                workflow = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                errors.append(f"invalid or missing workflow JSON: {directory.name}/{name}")
                continue
            if not isinstance(workflow, dict):
                errors.append(f"workflow metadata is not an object: {directory.name}/{name}")
                continue
            workflow_id = workflow.get("id")
            if not isinstance(workflow_id, str) or not workflow_id.strip():
                errors.append(f"missing stable workflow ID: {directory.name}/{name}")
            else:
                index.setdefault(workflow_id, []).append(name)
            if "active" in workflow and not isinstance(workflow["active"], bool):
                errors.append(f"invalid active metadata type: {directory.name}/{name}")
            settings = workflow.get("settings", {})
            if not isinstance(settings, dict):
                errors.append(f"invalid settings metadata type: {directory.name}/{name}")
                settings = {}
            if "errorWorkflow" in settings and not isinstance(settings["errorWorkflow"], str):
                errors.append(f"invalid errorWorkflow metadata type: {directory.name}/{name}")
            if workflow.get("active") is True:
                active_true_names.add(name)
            if directory == package:
                parsed[name] = workflow
                if workflow.get("id") != next((row.get("id") for row in rows if row.get("file") == name), None):
                    errors.append(f"inventory ID disagrees with packaged workflow: {name}")
                try:
                    source_workflow = json.loads((source / name).read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    source_workflow = None
                if source_workflow is not None and workflow != source_workflow:
                    errors.append(f"source/package workflow content differs: {name}")

    for label, index in (("package", by_id), ("canonical source", source_by_id)):
        for workflow_id, files in index.items():
            if len(files) > 1:
                errors.append(f"duplicate {label} workflow ID {workflow_id}: {', '.join(sorted(files))}")

    for name in sorted(active_true_names):
        errors.append(f"release blocked: active=true metadata: {name}")

    dispatcher = parsed.get("06_output_channel_dispatcher.json", {})
    for name, workflow in parsed.items():
        reference = (workflow.get("settings") or {}).get("errorWorkflow")
        if reference and reference not in by_id:
            errors.append(f"unresolved errorWorkflow reference: {name}")
    if dispatcher.get("id") != DISPATCHER_ID:
        errors.append("canonical dispatcher ID changed")
    if (dispatcher.get("settings") or {}).get("errorWorkflow") != ERROR_HANDLER_ID:
        errors.append("canonical dispatcher is missing its required global error-handler reference")
    if not any(w.get("id") == ERROR_HANDLER_ID for w in parsed.values()):
        errors.append("global error-handler workflow is missing from package")
    if inventory.get("n8n_workflows", {}).get("imported_inactive") is not True:
        errors.append("inventory does not declare the inactive import policy")
    if any("active=true metadata" in error for error in errors):
        errors.append("isolated target-like n8n import acceptance test is required before activation-state encoding can be approved")
    return errors


def main() -> int:
    errors = validate_release()
    if errors:
        for error in errors:
            print(error)
        return 1
    print("Canonical n8n release metadata is valid; target import acceptance is still required.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
