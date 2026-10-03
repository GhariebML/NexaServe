#!/usr/bin/env python3
"""Generate checksums for deployment artifacts"""
import hashlib, os, json, datetime, subprocess

artifacts = []
for root, dirs, files in os.walk('deployment'):
    dirs[:] = [d for d in dirs if d not in ('.git',)]
    for f in files:
        path = os.path.join(root, f)
        try:
            with open(path, 'rb') as fh:
                sha = hashlib.sha256(fh.read()).hexdigest()
            artifacts.append({'file': path, 'sha256': sha})
        except Exception:
            pass

manifest = {
    'generated': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'git_commit': subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip(),
    'version': '0.1.0',
    'artifacts': sorted(artifacts, key=lambda x: x['file'])
}

with open('deployment/MANIFEST.sha256', 'w', encoding='utf-8') as f:
    f.write('# NexaServe Deployment Manifest\n')
    f.write(f"# Version: {manifest['version']}\n")
    f.write(f"# Commit: {manifest['git_commit']}\n")
    f.write(f"# Generated: {manifest['generated']}\n\n")
    for a in manifest['artifacts']:
        f.write(f"{a['sha256']}  {a['file']}\n")

print(f"Generated manifest with {len(manifest['artifacts'])} artifacts")