import subprocess

workflows = [
    'CSWF000000000001',
    'CSWF000000000002',
    'CSWF000000000003',
    'CSWF000000000004',
    'CSWF000000000005',
    'CSWF000000000006',
    'RWLCadRzOPjTHXVo',
    'CSWF000000000007',
    'F7kjakLJXmzBDsvS',
    'CSWF000000000008',
    'MASTER_001',
    'MASTER_PROFESSIONAL_001'
]

for wf in workflows:
    print(f"Publishing {wf}...")
    res = subprocess.run(["docker", "exec", "cs-n8n", "n8n", "publish:workflow", f"--id={wf}"], capture_output=True, text=True)
    if res.returncode == 0:
        print(f"[SUCCESS] {wf} published successfully")
    else:
        print(f"[FAILED] {wf}: {res.stderr.strip()}")

print("Done publishing workflows!")

