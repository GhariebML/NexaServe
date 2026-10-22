"""Synthetic regression tests for the privacy-safe secret scanner."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
SCANNER_PATH = ROOT / "deployment" / "checks" / "verify_secrets.py"
SPEC = importlib.util.spec_from_file_location("verify_secrets", SCANNER_PATH)
assert SPEC and SPEC.loader
scanner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scanner)


class SecretScannerRegressionTests(unittest.TestCase):
    def test_empty_assignment_does_not_consume_next_environment_line(self) -> None:
        sample = "API_TOKEN=\nNEXT_SETTING=long-but-not-secret-config-value\n"
        self.assertNotIn("environment-secret-literal", scanner.scan_text(sample))

    def test_recognized_placeholders_are_not_reported(self) -> None:
        sample = "API_TOKEN=change-me-before-use\nDB_PASSWORD=${DB_PASSWORD}\n"
        self.assertNotIn("environment-secret-literal", scanner.scan_text(sample))

    def test_nonempty_secret_like_value_is_detected_without_returning_it(self) -> None:
        sample = "SERVICE_API_TOKEN=synthetic-test-only-value-1234567890\n"
        hits = scanner.scan_text(sample)
        self.assertIn("environment-secret-literal", hits)
        self.assertNotIn("synthetic-test-only-value-1234567890", repr(hits))


if __name__ == "__main__":
    unittest.main()
