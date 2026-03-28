#!/usr/bin/env python3
"""
Investigate over-full measures: are there still chord notes being counted?
"""
from pathlib import Path
from lxml import etree

# Check p002 P4 (active part with over-full measures)
mxl = 'tmp/crash_cache_v3/page_002/transform/CRASH_COMPLEXION_p002_transformed.xml'
tree = etree.parse(mxl)
parts = tree.xpath('//*[local-name()="part"]')

# P4 = index 3
part = parts[3]
measures = part.xpath('./*[local-name()="measure"]')
divs = 1

print('=== P4 measure analysis (voice-by-voice) ===')
for mi, m in enumerate(measures):
    dt = m.xpath('./*[local-name()="attributes"]/*[local-name()="divisions"]/text()')
    if dt:
        divs = int(dt[0])

    notes = m.xpath('./*[local-name()="note"]')
    mnum = m.get('number', str(mi+1))

    # Group by voice  
    voices: dict = {}
    for n in notes:
        voice = n.xpath('./*[local-name()="voice"]/text()')
        v = voice[0] if voice else '1'
        is_chord = bool(n.xpath('./*[local-name()="chord"]'))
        is_rest = bool(n.xpath('./*[local-name()="rest"]'))
        dur = n.xpath('./*[local-name()="duration"]/text()')
        beat_val = int(dur[0]) / divs if dur else 0

        if v not in voices:
            voices[v] = {'note_beats': 0.0, 'chord_beats': 0.0, 'count': 0}
        if is_chord:
            voices[v]['chord_beats'] += beat_val
        else:
            voices[v]['note_beats'] += beat_val
            voices[v]['count'] += 1

    # Total without chord
    total_no_chord = sum(v['note_beats'] for v in voices.values())
    total_with_chord = total_no_chord + sum(v['chord_beats'] for v in voices.values())
    
    # Max voice duration (correct measure length)
    max_voice = max((v['note_beats'] for v in voices.values()), default=0)

    status = 'OK' if abs(total_no_chord - 4.0) <= 0.125 else ('OVER' if total_no_chord > 4.0 else 'UNDER')
    print(f'  M{mnum:>3}: divs={divs} voices={list(voices.keys())} '
          f'total_no_chord={total_no_chord:.2f} max_voice={max_voice:.2f}  [{status}]')
    for vname, vdata in voices.items():
        print(f'       voice {vname}: {vdata["count"]} notes = {vdata["note_beats"]:.2f} beats'
              f'  (chord beats: {vdata["chord_beats"]:.2f})')

print()
print('=== KEY INSIGHT ===')
print('If total_no_chord > 4.0 but individual voices are ~4.0 each,')
print('then MULTI-VOICE polyphony is the cause (voices should be measured independently)')
