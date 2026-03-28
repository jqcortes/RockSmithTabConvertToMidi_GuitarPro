#!/usr/bin/env python3
"""Quick OMR matrix test - single case debug"""
import subprocess
import sys
import shutil
import json
from pathlib import Path

config = 'config/test_tab_on_035.properties'
cache = Path('tmp/omr_single_test')

if cache.exists():
    shutil.rmtree(cache)
cache.mkdir(parents=True)

shutil.copy(config, 'config/audiveris.properties')

cmd = [
    sys.executable, '-m', 'pipeline', 'convert',
    '--input', 'tests/fixtures/CRASH_COMPLEXION.pdf',
    '--output', str(cache / 'out.mid'),
    '--cache-dir', str(cache),
    '--default-role', 'guitar'
]

print(f'Running conversion...')
result = subprocess.run(cmd, timeout=900, capture_output=False)
print(f'Return code: {result.returncode}')

report = cache / 'quality_report.json'
if report.exists():
    with open(report) as f:
        data = json.load(f)
    print(f'Pages found: {len(data.get("pages", []))}')
    if len(data['pages']) > 1:
        p = data['pages'][1]
        print(f'p002: {p["stats"]["total_notes"]} notes, MC={p["metrics"]["measure_completeness"]:.4f}')
else:
    print('Report not found')
