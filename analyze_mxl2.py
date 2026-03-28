#!/usr/bin/env python3
"""Deep analyze MusicXML to find MC=0 root cause"""
from lxml import etree

mxl = 'tmp/crash_cache_v3/page_002/transform/CRASH_COMPLEXION_p002_transformed.xml'
tree = etree.parse(mxl)

parts = tree.xpath('//*[local-name()="part"]')
print(f'Total parts: {len(parts)}')

# Check raw attributes of first measure across all parts
print()
print('=== TIME SIGNATURE CHECK (all parts, measure 1) ===')
for pi, part in enumerate(parts):
    part_id = part.get('id')
    measures = part.xpath('./*[local-name()="measure"]')
    if not measures:
        print(f'  P{pi+1}: NO MEASURES')
        continue
    m0 = measures[0]
    # Raw XML dump of attributes
    attrs = m0.xpath('./*[local-name()="attributes"]')
    if attrs:
        time_el = attrs[0].xpath('.//*[local-name()="time"]')
        if time_el:
            beats = time_el[0].xpath('./*[local-name()="beats"]/text()')
            btype = time_el[0].xpath('./*[local-name()="beat-type"]/text()')
            print(f'  P{pi+1}: time={beats}/{btype}')
        else:
            print(f'  P{pi+1}: NO <time> element')
    else:
        print(f'  P{pi+1}: NO <attributes> element')

# Look at ALL measures of P1 to see beat totals
print()
print('=== ALL MEASURES of Part P1: beat analysis ===')
part0 = parts[0]
measures = part0.xpath('./*[local-name()="measure"]')
print(f'P1 has {len(measures)} measures')

divs_val = 1
time_sig = (4, 4)
for mi, m in enumerate(measures):
    # Update divisions
    divs_texts = m.xpath('./*[local-name()="attributes"]/*[local-name()="divisions"]/text()')
    if divs_texts:
        divs_val = int(divs_texts[0])
    # Update time sig
    beats_t = m.xpath('./*[local-name()="attributes"]/*[local-name()="time"]/*[local-name()="beats"]/text()')
    btype_t = m.xpath('./*[local-name()="attributes"]/*[local-name()="time"]/*[local-name()="beat-type"]/text()')
    if beats_t and btype_t:
        time_sig = (int(beats_t[0]), int(btype_t[0]))
    
    expected = time_sig[0] * (4.0 / time_sig[1])
    notes = m.xpath('./*[local-name()="note"]')
    total_dur = sum(int(n.xpath('./*[local-name()="duration"]/text()')[0]) / divs_val 
                    for n in notes if n.xpath('./*[local-name()="duration"]/text()'))
    note_count = len(notes)
    rest_count = len([n for n in notes if n.xpath('./*[local-name()="rest"]')])
    mnum = m.get('number', str(mi+1))
    status = "OK" if abs(total_dur - expected) <= 0.125 else "FAIL"
    print(f'  Measure {mnum:>4}: time={time_sig} divs={divs_val} expected={expected:.1f} '
          f'found={total_dur:.1f} notes={note_count} rests={rest_count} [{status}]')

# Count notes vs rests for all parts
print()
print('=== NOTE vs REST distribution per part ===')
for pi, part in enumerate(parts):
    all_notes = part.xpath('.//*[local-name()="note"]')
    rests = [n for n in all_notes if n.xpath('./*[local-name()="rest"]')]
    real = len(all_notes) - len(rests)
    print(f'  P{pi+1}: {real} real notes, {len(rests)} rests (total={len(all_notes)})')
