#!/usr/bin/env python3
"""Generate checksums for deployment artifacts"""
import hashlib, os, datetime, subprocess

artifacts = []
for root, dirs, files in os.walk('deployment'):
    dirs[:] = [d for d in dirs if d not in ('.git',)]
    for f in files:
        path = os.path.join(root, f)
        try:
            with open(path, 'rb') as fh:
                sha = hashlib.sha256(fh.read()).hexdigest()
            artifacts.append((path, sha))
        except Exception:
            pass

git_commit = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()

with open('deployment/MANIFEST.sha256', 'w', encoding='utf-8') as f:
    f.write('# NexaServe Deployment Manifest\n')
    f.write('# Version: 0.1.0\n')
    f.write(f'# Commit: {git_commit}\n')
    f.write(f'# Generated: {datetime.datetime.now(datetime.timezone.utc).isoformat()}\n\n')
    for path, sha in sorted(artifacts):
        f.write(f'{sha}  {path}\n')

print(f'Manifest: {len(artifacts)} artifacts')