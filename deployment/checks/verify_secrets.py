#!/usr/bin/env python3
"""Privacy-safe bundle scanner. Reports paths and rule names, never values."""

from __future__ import annotations

from pathlib import Path
import re
import sys


RULES = {
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "cloud-key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "github-token": re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{30,}\b"),
    "bearer-token": re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~-]{24,}"),
    "quoted-secret-value": re.compile(
        r"(?i)[\"'](?:[A-Z0-9_]*(?:PASSWORD|SECRET|API[_-]?KEY|TOKEN)[A-Z0-9_]*)"
        r"[\"']\s*:\s*[\"'](?!\$\{)(?!your\b|replace\b|change\b|example\b|"
        r"placeholder\b|generate\b)[A-Za-z0-9_./+=-]{16,}[\"']"
    ),
    # Horizontal whitespace is deliberate: \s can cross a newline and attribute
    # the next variable's value to an empty secret assignment.
    "environment-secret-literal": re.compile(
        r"(?m)^[ \t]*(?:export[ \t]+)?[A-Z0-9_]*(?:PASSWORD|SECRET|API[_-]?KEY|TOKEN)"
        r"[A-Z0-9_]*[ \t]*=[ \t]*(?!(?i:os\.getenv|os\.environ|getenv|process\.env|"
        r"None\b|False\b|True\b|your|replace|change|example|placeholder|generate|\$\{))"
        r"[\"']?[A-Za-z0-9_./+=-]{16,}"
    ),
}


def scan_text(text: str) -> set[str]:
    """Return matching rule names; never return or print matched values."""
    return {name for name, pattern in RULES.items() if pattern.search(text)}


def scan_tree(root: Path) -> list[tuple[str, str]]:
    hits: set[tuple[str, str]] = set()
    for path in root.rglob("*"):
        if not path.is_file() or path.name == ".env" or "offline" in path.parts:
            continue
        try:
            if path.stat().st_size > 5_000_000:
                continue
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        for rule in scan_text(text):
            hits.add((path.relative_to(root).as_posix(), rule))
    return sorted(hits)


def main() -> int:
    root = Path(sys.argv[1]).resolve()
    hits = scan_tree(root)
    if hits:
        for path, rule in hits:
            print(f"Potential {rule}: {path}")
        return 1
    if (root / "infra/n8n/credentials.json").exists():
        print("Unexpected n8n credentials export is present.")
        return 1
    print("No configured secret patterns found in bundle source; values are never printed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
