#!/usr/bin/env bash
set -Eeuo pipefail
here="$(cd -- "$(dirname -- "$0")/.." && pwd)"
python3 - "$here" <<'PY'
from pathlib import Path
import re,sys
root=Path(sys.argv[1])
rules={
 'private-key':re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
 'cloud-key':re.compile(r'\bAKIA[0-9A-Z]{16}\b'),
 'github-token':re.compile(r'\bgh[pousr]_[A-Za-z0-9_]{30,}\b'),
 'bearer-token':re.compile(r'(?i)\bBearer\s+[A-Za-z0-9._~-]{24,}'),
 'secret-assignment':re.compile(r'(?im)\b(?:password|passwd|secret|api[_-]?key|access[_-]?token)\b\s*[:=]\s*["\']?(?!\$\{)(?!your\b|replace\b|change\b|example\b|placeholder\b|generate\b)[A-Za-z0-9_./+=-]{16,}')
}
hits=[]
for p in root.rglob('*'):
 if not p.is_file() or p.name=='.env' or 'offline' in p.parts: continue
 try:
  if p.stat().st_size>5_000_000: continue
  t=p.read_text(encoding='utf-8')
 except (OSError,UnicodeError): continue
 for name,rx in rules.items():
  if rx.search(t): hits.append((p.relative_to(root).as_posix(),name))
if hits:
 for p,n in sorted(set(hits)): print(f'Potential {n}: {p}')
 sys.exit(1)
if (root/'infra/n8n/credentials.json').exists(): print('Unexpected n8n credentials export is present.'); sys.exit(1)
print('No configured secret patterns found in bundle source; values are never printed.')
PY
