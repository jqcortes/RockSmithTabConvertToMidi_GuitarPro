#!/usr/bin/env python3
"""
Diagnose remaining quality issues across all pages.
"""
from pathlib import Path
from lxml import etree
from pipeline.quality.metrics import QualityMetricsCalculator
from pipeline.quality.judge import QualityJudge

cache = Path('tmp/crash_cache_v3')
pages = sorted(cache.glob('page_*'))

print('=== REMAINING MC ISSUES: measure-by-measure breakdown ===')
print()

for page_dir in pages:
    pnum_str = page_dir.name.replace('page_', '')
    pnum = int(pnum_str)
    xml_path = page_dir / 'transform' / f'CRASH_COMPLEXION_p{pnum_str}_transformed.xml'
    if not xml_path.exists():
        continue

    tree = etree.parse(str(xml_path))
    parts = tree.xpath('//*[local-name()="part"]')
    
    # Find parts with real notes
    active_parts = []
    for p in parts:
        all_notes = p.xpath('.//*[local-name()="note"]')
        has_real = any(not n.xpath('./*[local-name()="rest"]') for n in all_notes)
        if has_real:
            active_parts.append(p)

    # Count measure quality
    total_m = 0
    ok_full = 0
    ok_partial = 0
    fail_over = 0
    fail_under = 0

    for part in active_parts:
        divs = 1
        time_sig = (4, 4)
        for m in part.xpath('./*[local-name()="measure"]'):
            dt = m.xpath('./*[local-name()="attributes"]/*[local-name()="divisions"]/text()')
            if dt:
                divs = int(dt[0])
            bt = m.xpath('./*[local-name()="attributes"]/*[local-name()="time"]/*[local-name()="beats"]/text()')
            btt = m.xpath('./*[local-name()="attributes"]/*[local-name()="time"]/*[local-name()="beat-type"]/text()')
            if bt and btt:
                time_sig = (int(bt[0]), int(btt[0]))

            notes = m.xpath('./*[local-name()="note"]')
            actual = 0.0
            for n in notes:
                if n.xpath('./*[local-name()="chord"]'):
                    continue
                dur = n.xpath('./*[local-name()="duration"]/text()')
                if dur:
                    actual += int(dur[0]) / divs

            if not notes:
                continue  # skip empty

            total_m += 1
            expected = time_sig[0] * (4.0 / time_sig[1])
            if abs(actual - expected) <= 0.125:
                ok_full += 1
            elif actual > expected:
                fail_over += 1
            else:
                fail_under += 1

    mc = QualityMetricsCalculator.calculate(tree)
    decision = QualityJudge.evaluate(mc)
    pct_ok = (ok_full / total_m * 100) if total_m > 0 else 0
    print(f'p{pnum:03}: MC={mc.measure_completeness:.3f} [{decision.judgment}]  '
          f'{total_m} active measures: '
          f'{ok_full} exact + {fail_over} over-full + {fail_under} under-full  '
          f'({pct_ok:.0f}% exact)')

print()
print('=== omr_confidence issue ===')
import json
with open('tmp/crash_v3/quality_report.json') as f:
    report = json.load(f)
for p in report['pages']:
    print(f"  p{p['page_number']:03}: omr_confidence={p['metrics']['omr_confidence']}")
