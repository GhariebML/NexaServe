#!/usr/bin/env python3
"""Explicitly activate an allowlisted n8n ingress workflow."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from n8n_release_policy import canonical_workflow_paths


ALLOWED_WORKFLOW_IDS = {"CSWF000000000001"}
ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--activate-workflow",
        required=True,
        choices=sorted(ALLOWED_WORKFLOW_IDS),
        help="explicitly activate one allowlisted workflow",
    )
    args = parser.parse_args()
    if not os.environ.get("N8N_ACTIVATION_APPROVED"):
        parser.error("set N8N_ACTIVATION_APPROVED in the approved operator environment")
    try:
        canonical_workflow_paths(ROOT)
    except Exception as exc:
        print(f"Release gate blocked activation ({type(exc).__name__}).", file=sys.stderr)
        return 1
    result = subprocess.run(
        ["docker", "exec", "cs-n8n", "n8n", "publish:workflow", f"--id={args.activate_workflow}"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        print("Activation command failed; no additional workflows were attempted.", file=sys.stderr)
        return result.returncode
    print(f"Activated allowlisted workflow {args.activate_workflow}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
