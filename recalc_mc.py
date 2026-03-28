#!/usr/bin/env python3
"""
Recalculate quality metrics from cached v3 MusicXML files using the FIXED metrics code.
"""
from pathlib import Path
from lxml import etree
from pipeline.quality.metrics import QualityMetricsCalculator

cache = Path('tmp/crash_cache_v3')
pages = sorted(cache.glob('page_*'))

print(f'=== Recalculated metrics (fixed MC) ===')
print(f'{"Page":<6} {"Notes":>6} {"Meas":>6} {"MC_old":>8} {"MC_new":>8} {"Diff":>8}')
print('-' * 55)

# Load old report for comparison
import json
with open('tmp/crash_v3/quality_report.json') as f:
    old_report = json.load(f)
old_by_page = {p['page_number']: p for p in old_report['pages']}

new_mc_values = []

for page_dir in pages:
    pnum_str = page_dir.name.replace('page_', '')
    pnum = int(pnum_str)
    
    xml_path = page_dir / 'transform' / f'CRASH_COMPLEXION_p{pnum_str}_transformed.xml'
    if not xml_path.exists():
        continue

    tree = etree.parse(str(xml_path))
    metrics = QualityMetricsCalculator.calculate(tree)
    
    old_p = old_by_page.get(pnum, {})
    old_mc = old_p.get('metrics', {}).get('measure_completeness', 0)
    diff = metrics.measure_completeness - old_mc
    
    new_mc_values.append(metrics.measure_completeness)
    
    print(f'p{pnum:03}   {metrics.total_notes:>6} {metrics.total_measures:>6} '
          f'{old_mc:>8.3f} {metrics.measure_completeness:>8.3f} {diff:>+8.3f}')

avg_new = sum(new_mc_values) / len(new_mc_values) if new_mc_values else 0
old_overall_mc = sum(p.get('metrics', {}).get('measure_completeness', 0) for p in old_report['pages']) / len(old_report['pages'])

print()
print(f'Average MC: {old_overall_mc:.3f} → {avg_new:.3f}  (improvement: {avg_new - old_overall_mc:+.3f})')
