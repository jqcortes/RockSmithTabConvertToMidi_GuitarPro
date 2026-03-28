#!/usr/bin/env python3
"""Analyze the parts that actually have notes (P4, P7, P8)"""
from lxml import etree

mxl = 'tmp/crash_cache_v3/page_002/transform/CRASH_COMPLEXION_p002_transformed.xml'
tree = etree.parse(mxl)
parts = tree.xpath('//*[local-name()="part"]')

# Focus on parts with real notes: P4=idx3, P7=idx6, P8=idx7
target_parts = [3, 6, 7]  # 0-indexed

for pi in target_parts:
    part = parts[pi]
    part_id = part.get('id')
    all_notes = part.xpath('.//*[local-name()="note"]')
    rests = [n for n in all_notes if n.xpath('./*[local-name()="rest"]')]
    real = len(all_notes) - len(rests)
    
    measures = part.xpath('./*[local-name()="measure"]')
    print(f'\n=== Part {part_id} ({real} real notes, {len(rests)} rests) ===')
    
    divs_val = 1
    time_sig = (4, 4)
    for mi, m in enumerate(measures):
        divs_texts = m.xpath('./*[local-name()="attributes"]/*[local-name()="divisions"]/text()')
        if divs_texts:
            divs_val = int(divs_texts[0])
        
        expected = time_sig[0] * (4.0 / time_sig[1])
        notes = m.xpath('./*[local-name()="note"]')
        
        note_total = 0.0
        rest_total = 0.0
        real_notes = 0
        for n in notes:
            dur = n.xpath('./*[local-name()="duration"]/text()')
            is_rest = bool(n.xpath('./*[local-name()="rest"]'))
            is_chord = bool(n.xpath('./*[local-name()="chord"]'))
            if dur:
                beat_val = int(dur[0]) / divs_val
                if not is_chord:  # only count non-chord notes for measure length
                    if is_rest:
                        rest_total += beat_val
                    else:
                        note_total += beat_val
                        real_notes += 1
        
        total = note_total + rest_total
        status = "OK" if abs(total - expected) <= 0.125 else "FAIL"
        mnum = m.get('number', str(mi+1))
        print(f'  M{mnum:>3}: divs={divs_val:>4} E={expected:.1f} found={total:.2f} '
              f'(real={note_total:.2f} rests={rest_total:.2f}) [{status}] '
              f'{real_notes} real notes')

# Also check p008 (the MC=0.000 case)
print('\n\n=== PAGE 8 ANALYSIS ===')
mxl8 = 'tmp/crash_cache_v3/page_008/transform/CRASH_COMPLEXION_p008_transformed.xml'
tree8 = etree.parse(mxl8)
parts8 = tree8.xpath('//*[local-name()="part"]')
print(f'P008 parts: {len(parts8)}')
for pi, part in enumerate(parts8):
    all_notes = part.xpath('.//*[local-name()="note"]')
    rests = [n for n in all_notes if n.xpath('./*[local-name()="rest"]')]
    real = len(all_notes) - len(rests)
    if real > 0:
        measures = part.xpath('./*[local-name()="measure"]')
        print(f'  Part P{pi+1}: {real} real notes, {len(rests)} rests, {len(measures)} measures')
        divs_val = 1
        for mi, m in enumerate(measures[:3]):
            divs_texts = m.xpath('./*[local-name()="attributes"]/*[local-name()="divisions"]/text()')
            if divs_texts:
                divs_val = int(divs_texts[0])
            notes = m.xpath('./*[local-name()="note"]')
            total = sum(int(n.xpath('./*[local-name()="duration"]/text()')[0]) / divs_val
                       for n in notes if n.xpath('./*[local-name()="duration"]/text()'))
            mnum = m.get('number', str(mi+1))
            print(f'    M{mnum}: divs={divs_val} found={total:.2f}')
