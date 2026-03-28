#!/usr/bin/env python3
import json

with open('tmp/crash_v3/quality_report.json') as f:
    r = json.load(f)

print('=== OVERALL ===')
print(f'  overall_score : {r["overall_score"]}')
print(f'  judgment      : {r["judgment"]}')
print(f'  total_pages   : {len(r["pages"])}')

print()
print('=== PER PAGE ===')
hdr = f'{"Page":<6} {"Notes":>6} {"Meas":>6} {"MC":>8} {"Score":>8} {"Filtered":>8} Judgment'
print(hdr)
print('-' * 60)
for p in r['pages']:
    n = p['page_number']
    notes = p['stats']['total_notes']
    meas  = p['stats']['total_measures']
    mc    = p['metrics']['measure_completeness']
    score = p['overall_score']
    filt  = p['stats'].get('filtered_notes', 0)
    judg  = p.get('judgment', '?')
    row = f'p{n:03}   {notes:>6} {meas:>6} {mc:>8.3f} {score:>8.3f} {filt:>8}  {judg}'
    print(row)

print()
print('=== WARNINGS / ERRORS PER PAGE ===')
for p in r['pages']:
    n = p['page_number']
    warns = p.get('warnings', [])
    if warns:
        print(f'p{n:03}: {len(warns)} warnings')
        for w in warns[:5]:
            print(f'  - {w}')

print()
print('=== METRICS DETAIL (first 3 pages) ===')
for p in r['pages'][:3]:
    n = p['page_number']
    print(f'\n-- p{n:03} --')
    for k, v in p['metrics'].items():
        print(f'  {k}: {v}')
