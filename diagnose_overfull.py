#!/usr/bin/env python3
"""
Look at the actual raw XML of an over-full measure to understand Audiveris output.
"""
from pathlib import Path
from lxml import etree

mxl = 'tmp/crash_cache_v3/page_002/transform/CRASH_COMPLEXION_p002_transformed.xml'
tree = etree.parse(mxl)
parts = tree.xpath('//*[local-name()="part"]')

# P4 = index 3, Measure 1 (over-full, 6.0 beats for 4/4)
part = parts[3]
m = part.xpath('./*[local-name()="measure"]')[0]
print(f'=== Raw XML: P4 Measure 1 ===')
print(f'Expected: 4.0 beats (4/4)')
print()

divs = 12
notes = m.xpath('./*[local-name()="note"]')
cumulative = 0.0
print(f'{"#":>3} {"chord":>6} {"rest":>5} {"dur":>6} {"beats":>7} {"cumul":>7} {"type":>12} {"pitch":>10}')
print('-' * 70)
for i, n in enumerate(notes):
    is_chord = bool(n.xpath('./*[local-name()="chord"]'))
    is_rest = bool(n.xpath('./*[local-name()="rest"]'))
    dur = n.xpath('./*[local-name()="duration"]/text()')
    typ = n.xpath('./*[local-name()="type"]/text()')
    
    # pitch
    step = n.xpath('./*[local-name()="pitch"]/*[local-name()="step"]/text()')
    octave = n.xpath('./*[local-name()="pitch"]/*[local-name()="octave"]/text()')
    pitch_str = f'{step[0]}{octave[0]}' if step and octave else ('rest' if is_rest else '?')
    
    beat_val = int(dur[0]) / divs if dur else 0
    if not is_chord:
        cumulative += beat_val
    
    print(f'{i+1:>3} {str(is_chord):>6} {str(is_rest):>5} {dur[0] if dur else "?":>6} '
          f'{beat_val:>7.3f} {cumulative:>7.3f} {typ[0] if typ else "?":>12} {pitch_str:>10}')

print()
print(f'Total cumulative: {cumulative:.3f} (chord notes not counted)')
print()
print('=== HYPOTHESIS: Are some "notes" actually backup/forward elements? ===')
# Check all children
for child in m:
    tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
    if tag not in ('note', 'attributes', 'barline', 'print'):
        print(f'  Found: <{tag}>')
        
print()
print('=== Check p008 M1 (MC=0.891 but 0% exact, all over/under-full) ===')
mxl8 = 'tmp/crash_cache_v3/page_008/transform/CRASH_COMPLEXION_p008_transformed.xml'
tree8 = etree.parse(mxl8)
parts8 = tree8.xpath('//*[local-name()="part"]')
# P2 has 94 real notes
part8 = parts8[1]
measures8 = part8.xpath('./*[local-name()="measure"]')
divs8 = 1
print(f'P2 has {len(measures8)} measures')
for mi, m8 in enumerate(measures8[:3]):
    dt = m8.xpath('./*[local-name()="attributes"]/*[local-name()="divisions"]/text()')
    if dt:
        divs8 = int(dt[0])
    notes8 = m8.xpath('./*[local-name()="note"]')
    actual = sum(int(n.xpath('./*[local-name()="duration"]/text()')[0]) / divs8
                 for n in notes8
                 if n.xpath('./*[local-name()="duration"]/text()')
                 and not n.xpath('./*[local-name()="chord"]'))
    chords = sum(1 for n in notes8 if n.xpath('./*[local-name()="chord"]'))
    print(f'  M{mi+1}: divs={divs8} total={actual:.2f} ({len(notes8)} notes, {chords} chords)')
