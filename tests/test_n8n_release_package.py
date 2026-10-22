"""Offline release invariants for the canonical n8n workflow set."""

from __future__ import annotations

import hashlib
import importlib.util
import fnmatch
import ast
import json
import re
import sys
import unittest
from unittest.mock import patch
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
PACKAGE = ROOT / "deployment" / "assets" / "n8n" / "workflows"
SOURCE = ROOT / "infra" / "n8n" / "workflows"
CANONICAL_NAME = "06_output_channel_dispatcher.json"
CANONICAL_ID = "F7kjakLJXmzBDsvS"
ERROR_HANDLER_ID = "CSWF000000000008"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def import_from_path(name: str, path: Path):
    scripts_dir = str(ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class N8nReleasePackageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.inventory = read_json(ROOT / "deployment" / "inventory.json")
        self.rows = self.inventory["workflows"]
        self.names = [row["file"] for row in self.rows]
        self.source_workflows = [(SOURCE / name, read_json(SOURCE / name)) for name in self.names]
        self.package_workflows = [(PACKAGE / name, read_json(PACKAGE / name)) for name in self.names]
        self.by_id: dict[str, list[tuple[Path, dict]]] = {}
        for path, workflow in self.package_workflows:
            self.by_id.setdefault(workflow.get("id", ""), []).append((path, workflow))

    def test_inventory_selection_has_unique_ids_and_one_dispatcher(self) -> None:
        self.assertEqual(len(self.names), len(set(self.names)))
        source_ids = [workflow.get("id") for _, workflow in self.source_workflows]
        package_ids = [workflow.get("id") for _, workflow in self.package_workflows]
        self.assertTrue(all(isinstance(item, str) and item for item in source_ids + package_ids))
        self.assertEqual(len(source_ids), len(set(source_ids)))
        self.assertEqual(len(package_ids), len(set(package_ids)))
        self.assertEqual({path.name for path in PACKAGE.glob("*.json")}, set(self.names))
        entries = self.by_id[CANONICAL_ID]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0][0].name, CANONICAL_NAME)

    def test_legacy_duplicate_ids_are_excluded_from_import_selection(self) -> None:
        inventory_names = set(self.names)
        self.assertNotIn("02_customer_session_manager.json", inventory_names)
        self.assertNotIn("08_global_error_handler.json", inventory_names)
        # These legacy files duplicate IDs among all source JSON; importers must use inventory.
        for legacy_name in ("02_customer_session_manager.json", "08_global_error_handler.json"):
            self.assertTrue((SOURCE / legacy_name).exists())
        powershell_import = (ROOT / "scripts" / "import-workflows.ps1").read_text(encoding="utf-8")
        self.assertIn("deployment\\inventory.json", powershell_import)
        for relative in ("scripts/push-workflows-api.py", "scripts/patch_and_deploy_workflows.py"):
            content = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("canonical_workflow_paths", content, relative)
            self.assertNotRegex(content, r"glob\.glob\([^\n]*infra/n8n/workflows/\*\.json")

    def test_all_source_workflow_ids_and_metadata_are_accounted_for(self) -> None:
        source_files = sorted(SOURCE.glob("*.json"))
        ids: dict[str, set[str]] = {}
        for path in source_files:
            workflow = read_json(path)
            self.assertIsInstance(workflow.get("id"), str, path.name)
            if "active" in workflow:
                self.assertIsInstance(workflow["active"], bool, path.name)
            self.assertIsInstance(workflow.get("settings", {}), dict, path.name)
            ids.setdefault(workflow["id"], set()).add(path.name)
        duplicates = {workflow_id: names for workflow_id, names in ids.items() if len(names) > 1}
        self.assertEqual(
            duplicates,
            {
                "CSWF000000000002": {"02_customer_session.json", "02_customer_session_manager.json"},
                "CSWF000000000008": {"00_global_error_handler.json", "08_global_error_handler.json"},
            },
        )

    def test_all_package_json_and_graphs_are_well_formed(self) -> None:
        for path, workflow in self.package_workflows:
            with self.subTest(workflow=path.name):
                self.assertIsInstance(workflow.get("id"), str)
                if "active" in workflow:
                    self.assertIsInstance(workflow["active"], bool)
                self.assertIsInstance(workflow.get("settings", {}), dict)
                error_workflow = (workflow.get("settings") or {}).get("errorWorkflow")
                if error_workflow is not None:
                    self.assertIsInstance(error_workflow, str)
                nodes = workflow.get("nodes")
                self.assertIsInstance(nodes, list)
                names = [node.get("name") for node in nodes]
                ids = [node.get("id") for node in nodes]
                self.assertTrue(all(names))
                self.assertEqual(len(names), len(set(names)))
                self.assertTrue(all(ids))
                self.assertEqual(len(ids), len(set(ids)))
                for source_name, connection in workflow.get("connections", {}).items():
                    self.assertIn(source_name, names)
                    for outputs in connection.values():
                        for group in outputs:
                            for target in group:
                                self.assertIn(target.get("node"), names)

    def test_source_and_package_definitions_match_completely(self) -> None:
        source = {path.name: workflow for path, workflow in self.source_workflows}
        packaged = {path.name: workflow for path, workflow in self.package_workflows}
        self.assertEqual(set(source), set(packaged))
        for name in self.names:
            with self.subTest(workflow=name):
                self.assertEqual(source[name], packaged[name])
        dispatcher = packaged[CANONICAL_NAME]
        self.assertEqual(dispatcher["id"], CANONICAL_ID)
        self.assertEqual(dispatcher["settings"]["errorWorkflow"], ERROR_HANDLER_ID)

    def test_required_error_handler_reference_exists(self) -> None:
        known_ids = set(self.by_id)
        for _, workflow in self.package_workflows:
            reference = (workflow.get("settings") or {}).get("errorWorkflow")
            if reference:
                self.assertIn(reference, known_ids)
        refs = [w for _, w in self.package_workflows if (w.get("settings") or {}).get("errorWorkflow") == ERROR_HANDLER_ID]
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0]["id"], CANONICAL_ID)
        self.assertEqual(len(self.by_id[ERROR_HANDLER_ID]), 1)
        self.assertEqual(self.by_id[ERROR_HANDLER_ID][0][0].name, "00_global_error_handler.json")

    def test_inventory_sync_and_release_manifest_select_canonical(self) -> None:
        dispatcher_rows = [row for row in self.rows if row.get("id") == CANONICAL_ID]
        self.assertEqual(len(dispatcher_rows), 1)
        self.assertEqual(dispatcher_rows[0]["file"], CANONICAL_NAME)
        sync_source = (ROOT / "scripts" / "sync_deployment.py").read_text(encoding="utf-8")
        sync_tree = ast.parse(sync_source)
        canonical_assignment = next(
            node for node in sync_tree.body
            if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "canonical" for target in node.targets)
        )
        sync_names = ast.literal_eval(canonical_assignment.value)
        self.assertEqual(set(sync_names), set(self.names))
        release_manifest = (ROOT / "docs" / "RELEASE_MANIFEST.md").read_text(encoding="utf-8")
        self.assertIn(f"deployment/assets/n8n/workflows/{CANONICAL_NAME}", release_manifest)
        self.assertNotIn("deployment/assets/n8n/workflows/06_output_dispatcher.json", release_manifest)

    def test_activation_scripts_are_opt_in_allowlisted_or_import_only(self) -> None:
        deployment_import = (ROOT / "deployment" / "scripts" / "deploy_workflows.sh").read_text(encoding="utf-8")
        ps_import = (ROOT / "scripts" / "import-workflows.ps1").read_text(encoding="utf-8")
        patch_import = (ROOT / "scripts" / "patch_and_deploy_workflows.py").read_text(encoding="utf-8")
        api_import = (ROOT / "scripts" / "push-workflows-api.py").read_text(encoding="utf-8")
        publisher = (ROOT / "scripts" / "publish_workflows.py").read_text(encoding="utf-8")
        updater = (ROOT / "scripts" / "publish_and_test.py").read_text(encoding="utf-8")
        restore = (ROOT / "scripts" / "restore.ps1").read_text(encoding="utf-8")
        discover = (ROOT / "scripts" / "discover_api.py").read_text(encoding="utf-8")
        sync = (ROOT / "scripts" / "sync_deployment.py").read_text(encoding="utf-8")
        bundle_test = (ROOT / "deployment" / "tests" / "deployment" / "check_bundle.sh").read_text(encoding="utf-8")
        self.assertNotIn("publish:workflow", deployment_import + ps_import + patch_import)
        self.assertNotIn("/activate", deployment_import + ps_import + patch_import + restore)
        self.assertIn("validate_n8n_release.py", deployment_import)
        self.assertIn("validate_n8n_release.py", bundle_test)
        self.assertIn("active=true", ps_import)
        self.assertIn("import_acceptance", ps_import)
        self.assertIn("--activate-workflow", api_import)
        self.assertIn("validate_activation_ids", api_import)
        self.assertIn("default=[]", api_import)
        self.assertIn("activate_ids: list[str]", api_import)
        self.assertIn("N8N_ACTIVATION_APPROVED", api_import)
        self.assertLess(api_import.index("for path, workflow in exports"), api_import.index("/activate"))
        self.assertIn("no later activation was attempted", api_import)
        self.assertIn("required=True", publisher)
        self.assertIn("choices=sorted(ALLOWED_WORKFLOW_IDS)", publisher)
        self.assertIn("N8N_ACTIVATION_APPROVED", publisher)
        self.assertIn("canonical_workflow_paths(ROOT)", publisher)
        self.assertIn("ACTIVATABLE_WORKFLOW_IDS", (ROOT / "scripts" / "n8n_release_policy.py").read_text(encoding="utf-8"))

        dashboard = (ROOT / "dashboard" / "backend" / "routes.py").read_text(encoding="utf-8")
        activation = dashboard.split("async def activate_n8n_workflow", 1)[1].split("@router.post", 1)[0]
        self.assertIn("N8N_ACTIVATABLE_WORKFLOW_IDS", activation)
        self.assertIn("N8N_ACTIVATION_APPROVED", activation)
        self.assertIn("N8N_IMPORT_ACCEPTANCE_VERIFIED", activation)
        self.assertNotIn('method="POST"', discover)
        self.assertNotIn("publish:workflow", sync)
        self.assertNotIn("/activate", updater)
        self.assertIn("--update-workflow", updater)
        self.assertIn("N8N_UPDATE_APPROVED", updater)
        self.assertIn("choices=sorted(ALLOWED_WORKFLOWS)", updater)
        self.assertIn("active=true update blocked", updater)
        self.assertIn("canonical_workflow_paths(ROOT)", updater)
        self.assertIn("active=true metadata", restore)
        self.assertIn("import_acceptance", restore)
        self.assertIn("no activation was attempted", restore)

    def test_api_import_failure_does_not_fall_through_to_activation(self) -> None:
        importer = import_from_path("push_api_importer_test", ROOT / "scripts" / "push-workflows-api.py")
        calls: list[str] = []

        def fake_request(url: str, headers: dict, *, method: str = "GET", payload: dict | None = None) -> dict:
            calls.append(url)
            if method == "GET":
                return {"data": [{"id": CANONICAL_ID}]}
            raise RuntimeError("synthetic import failure")

        with patch.object(importer, "canonical_workflow_paths", return_value=[SOURCE / CANONICAL_NAME]), patch.object(
            importer, "request_json", side_effect=fake_request
        ):
            with self.assertRaisesRegex(RuntimeError, "synthetic import failure"):
                importer.run(
                    activate_ids=["CSWF000000000001"],
                    api_key="synthetic-test-only",
                    base_url="http://no-network.invalid/api/v1",
                )
        self.assertFalse(any("/activate" in url for url in calls))

    def test_release_gate_blocks_active_true_and_invalid_activation_metadata(self) -> None:
        validator = import_from_path("n8n_release_validator", ROOT / "deployment" / "checks" / "validate_n8n_release.py")
        errors = validator.validate_release(ROOT)
        active_blockers = [error for error in errors if "active=true metadata" in error]
        blocked_files = {error.rsplit(": ", 1)[-1] for error in active_blockers}
        self.assertEqual(len(blocked_files), 6)
        self.assertTrue(any("isolated target-like" in error for error in errors))
        self.assertTrue(any("acceptance evidence is not recorded" in error for error in errors))
        self.assertEqual(self.inventory["n8n_workflows"]["imported_inactive"], True)
        policy = import_from_path("n8n_release_policy", ROOT / "scripts" / "n8n_release_policy.py")
        with self.assertRaisesRegex(ValueError, "acceptance evidence is not recorded"):
            policy.canonical_workflow_paths(ROOT)
        policy.validate_activation_ids(["CSWF000000000001"])
        with self.assertRaisesRegex(ValueError, "outside the allowlist"):
            policy.validate_activation_ids([CANONICAL_ID])
        for _, workflow in self.package_workflows:
            if "active" in workflow:
                self.assertIsInstance(workflow["active"], bool)

    def test_credential_export_policy_is_checked_in_package(self) -> None:
        deployment = ROOT / "deployment"
        for path, workflow in self.package_workflows:
            for node in workflow.get("nodes", []):
                for reference in (node.get("credentials") or {}).values():
                    self.assertLessEqual(set(reference), {"id", "name"}, f"{path.name}:{node.get('name')}")
        for path in deployment.rglob("*"):
            if not path.is_file():
                continue
            self.assertFalse(
                any(fnmatch.fnmatch(path.name, pattern) for pattern in ("*credentials.json", "*.dump", "*.secret", "*.pem", "*.key")),
                path.relative_to(ROOT),
            )
        scanner = import_from_path("bundle_secret_scanner", deployment / "checks" / "verify_secrets.py")
        self.assertEqual(scanner.scan_tree(deployment), [])
        docs = (ROOT / "deployment" / "docs" / "n8n.md").read_text(encoding="utf-8")
        self.assertIn("Credential definitions and secrets are excluded", docs)
        self.assertIn("non-secret credential references may remain", docs)

    def test_manifest_tracks_all_deployment_files_except_declared_exclusions(self) -> None:
        deployment = ROOT / "deployment"
        manifest_bytes = (deployment / "MANIFEST.sha256").read_bytes()
        self.assertNotIn(b"\r\n", manifest_bytes)
        records: dict[str, str] = {}
        for line in manifest_bytes.decode("utf-8").splitlines():
            # GNU sha256sum emits either text mode (two spaces) or binary mode (space + '*').
            match = re.fullmatch(r"([0-9a-f]{64}) (?: |\*)(.+)", line)
            self.assertIsNotNone(match, "malformed checksum entry")
            digest, relative = match.groups()
            self.assertTrue(relative.startswith("./"))
            records[relative.removeprefix("./")] = digest
        expected: set[str] = set()
        for path in deployment.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(deployment).as_posix()
            if relative == "MANIFEST.sha256" or relative == ".env" or relative.startswith("offline-package/"):
                continue
            if "__pycache__" in path.parts or path.suffix in {".pyc", ".log"}:
                continue
            expected.add(relative)
        self.assertEqual(set(records), expected)
        self.assertEqual(list(records), sorted(records))
        for relative, digest in records.items():
            self.assertEqual(hashlib.sha256((deployment / relative).read_bytes()).hexdigest(), digest, relative)
        attrs = (ROOT / ".gitattributes").read_text(encoding="utf-8")
        self.assertIn("/deployment/MANIFEST.sha256 text eol=lf", attrs)


if __name__ == "__main__":
    unittest.main()
