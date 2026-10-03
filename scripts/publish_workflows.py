import subprocess

workflows = [
    # Only the canonical HTTP ingress owns /webhook/customer-service.
    'CSWF000000000001'
]

for wf in workflows:
    print(f"Publishing {wf}...")
    res = subprocess.run(["docker", "exec", "cs-n8n", "n8n", "publish:workflow", f"--id={wf}"], capture_output=True, text=True)
    if res.returncode == 0:
        print(f"[SUCCESS] {wf} published successfully")
    else:
        print(f"[FAILED] {wf}: {res.stderr.strip()}")

print("Done publishing workflows!")

