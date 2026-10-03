#!/usr/bin/env python3
import json

with open('tests/final_test_results.json', 'r') as f:
    data = json.load(f)

print('=== PYTHON SYNTAX FAILURES ===')
for path, result in data['tests']['python_syntax']['details'].items():
    if 'FAIL' in result:
        print(f'  {path}: {result}')

print('\n=== SHELL SYNTAX FAILURES ===')
for path, result in data['tests']['shell_syntax']['details'].items():
    if 'FAIL' in result:
        print(f'  {path}: {result}')