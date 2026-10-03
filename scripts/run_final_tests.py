#!/usr/bin/env python3
"""Run all available tests and collect results"""
import subprocess, json, os, sys, datetime

results = {
    'timestamp': datetime.datetime.utcnow().isoformat() + 'Z',
    'tests': {}
}

# 1. Secret scan
r = subprocess.run(['python', 'scripts/secret_scan.py'], capture_output=True, text=True)
results['tests']['secret_scan'] = {'returncode': r.returncode, 'output': r.stdout.strip()}

# 2. Python syntax checks
syntax_results = {}
errors = 0
for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if d not in ('.git', 'node_modules', '__pycache__', '.kilo', 'backups', 'data')]
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            r = subprocess.run(['python', '-m', 'py_compile', path], capture_output=True, text=True)
            if r.returncode != 0:
                syntax_results[path] = f'FAIL: {r.stderr[:200]}'
                errors += 1
            else:
                syntax_results[path] = 'PASS'
results['tests']['python_syntax'] = {'total': len(syntax_results), 'failed': errors, 'details': syntax_results}

# 3. YAML checks
yaml_results = {}
for f in ['docker-compose.yml', 'deployment/compose/docker-compose.yml']:
    if os.path.exists(f):
        try:
            import yaml
            with open(f) as fh:
                yaml.safe_load(fh)
            yaml_results[f] = 'PASS'
        except Exception as e:
            yaml_results[f] = f'FAIL: {e}'
results['tests']['yaml_checks'] = yaml_results

# 4. Shell syntax checks
shell_results = {}
shell_errors = 0
for root, dirs, files in os.walk('deployment'):
    for f in files:
        if f.endswith('.sh'):
            path = os.path.join(root, f)
            r = subprocess.run(['bash', '-n', path], capture_output=True, text=True)
            if r.returncode != 0:
                shell_results[path] = f'FAIL: {r.stderr[:200]}'
                shell_errors += 1
            else:
                shell_results[path] = 'PASS'
results['tests']['shell_syntax'] = {'total': len(shell_results), 'failed': shell_errors, 'details': shell_results}

# 5. Docker Compose config
r = subprocess.run(['docker', 'compose', 'config', '--quiet'], capture_output=True, text=True)
results['tests']['docker_compose_config'] = {'returncode': r.returncode, 'output': (r.stderr[:500] if r.stderr else 'OK')}

# 6. JSON validation for workflows
wf_results = {}
wf_errors = 0
wf_dir = 'infra/n8n/workflows'
for f in sorted(os.listdir(wf_dir)):
    if f.endswith('.json'):
        path = os.path.join(wf_dir, f)
        try:
            with open(path, encoding='utf-8') as fh:
                json.load(fh)
            wf_results[f] = 'PASS'
        except Exception as e:
            wf_results[f] = f'FAIL: {e}'
            wf_errors += 1
results['tests']['workflow_json'] = {'total': len(wf_results), 'failed': wf_errors, 'details': wf_results}

# Write results to file
with open('tests/final_test_results.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2, default=str)

# Print summary
print('=== TEST RESULTS ===')
print(f"Secret scan: {'PASS' if results['tests']['secret_scan']['returncode'] == 0 else 'FAIL'}")
print(f"Python syntax: {results['tests']['python_syntax']['total'] - errors}/{results['tests']['python_syntax']['total']} passed")
print(f"YAML checks: {list(yaml_results.values())}")
print(f"Shell syntax: {results['tests']['shell_syntax']['total'] - shell_errors}/{results['tests']['shell_syntax']['total']} passed")
print(f"Docker compose config: {'PASS' if r.returncode == 0 else 'FAIL'}")
print(f"Workflow JSON: {results['tests']['workflow_json']['total'] - wf_errors}/{results['tests']['workflow_json']['total']} passed")