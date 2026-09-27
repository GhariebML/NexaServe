#!/usr/bin/env python3
"""Privacy-safe source secret scanner. Reports file/rule only, never matched text."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".kilo", ".opencode", "backups", "data", "scratch", ".pytest_cache"}
SKIP_FILES = {".env", "secret_scan.py"}
RULES = {
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "cloud-access-key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "github-token": re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{30,}\b"),
    "bearer-token-literal": re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~-]{24,}"),
    "secret-assignment": re.compile(r"(?im)\b(?:password|passwd|secret|api[_-]?key|access[_-]?token)\b\s*[:=]\s*[\"']?(?!\$\{)(?!your\b|replace\b|change\b|example\b|placeholder\b|generate\b)[A-Za-z0-9_./+=-]{16,}"),
}
findings = []
for folder, dirs, names in __import__("os").walk(ROOT):
    dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
    for name in names:
        if name in SKIP_FILES:
            continue
        path = Path(folder) / name
        try:
            if path.stat().st_size > 5_000_000:
                continue
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        for rule, pattern in RULES.items():
            if pattern.search(text):
                findings.append((path.relative_to(ROOT).as_posix(), rule))
if findings:
    print("Potential secret patterns found (matched values suppressed):")
    for path, rule in sorted(set(findings)):
        print(f"  {path}: {rule}")
    sys.exit(1)
print("SECRET SCAN: no configured credential patterns in scanned source files; local .env/backups/data are excluded.")
