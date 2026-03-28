#!/usr/bin/env python3
"""Analyze p002 MusicXML structure to find MC calculation bug"""
from lxml import etree

mxl = 'tmp/crash_cache_v3/page_002/transform/CRASH_COMPLEXION_p002_transformed.xml'
tree = etree.parse(mxl)

parts = tree.xpath('//*[local-name()="part"]')
print(f'Total parts: {len(parts)}')

print()
print('=== FIRST 3 PARTS: first measure analysis ===')
for pi, part in enumerate(parts[:3]):
    part_id = part.get('id')
    measures = part.xpath('./*[local-name()="measure"]')
    print(f'\n--- Part[{pi}] id={part_id} ({len(measures)} measures) ---')
    
    m0 = measures[0]
    attrs = m0.xpath('./*[local-name()="attributes"]')
    divs_val = 1
    if attrs:
        a = attrs[0]
        divs = a.xpath('./*[local-name()="divisions"]/text()')
        beats = a.xpath('./*[local-name()="time"]/*[local-name()="beats"]/text()')
        btype = a.xpath('./*[local-name()="time"]/*[local-name()="beat-type"]/text()')
        if divs:
            divs_val = int(divs[0])
        print(f'  divisions={divs} time={beats}/{btype}')
    
    notes = m0.xpath('./*[local-name()="note"]')
    total_dur = 0.0
    print(f'  Notes: {len(notes)}')
    for n in notes[:8]:
        dur = n.xpath('./*[local-name()="duration"]/text()')
        typ = n.xpath('./*[local-name()="type"]/text()')
        rest = n.xpath('./*[local-name()="rest"]')
        chord = n.xpath('./*[local-name()="chord"]')
        beat_val = int(dur[0]) / divs_val if dur else 0
        total_dur += beat_val
        print(f'    dur={dur} type={typ} rest={bool(rest)} chord={bool(chord)} => {beat_val:.3f} beats')
    if len(notes) > 8:
        print(f'    ... ({len(notes)-8} more notes)')
    print(f'  Measure total: {total_dur:.3f} beats (expected ~4.0 for 4/4)')

print()
print('=== score-part names ===')
for sp in tree.xpath('//*[local-name()="score-part"]'):
    sid = sp.get('id')
    name = sp.xpath('./*[local-name()="part-name"]/text()')
    role_attr = sp.xpath('@*[local-name()="role"]')
    print(f'  {sid}: {name} role={role_attr}')
