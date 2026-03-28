#!/usr/bin/env python3
from lxml import etree
from pathlib import Path
f = Path('tests/fixtures/musicxml/quality_measure_incomplete.xml')
tree = etree.parse(str(f))
parts = tree.xpath('//*[local-name()="part"]')
print(f'Parts: {len(parts)}')
for pi, part in enumerate(parts):
    all_notes = part.xpath('.//*[local-name()="note"]')
    rests = [n for n in all_notes if n.xpath('./*[local-name()="rest"]')]
    real = len(all_notes) - len(rests)
    print(f'  P{pi+1}: {real} real notes, {len(rests)} rests')
    measures = part.xpath('./*[local-name()="measure"]')
    for mi, m in enumerate(measures):
        notes = m.xpath('./*[local-name()="note"]')
        divs = m.xpath('./*[local-name()="attributes"]/*[local-name()="divisions"]/text()')
        dv = int(divs[0]) if divs else 1
        total = sum(
            int(n.xpath('./*[local-name()="duration"]/text()')[0]) / dv
            for n in notes if n.xpath('./*[local-name()="duration"]/text()')
            and not n.xpath('./*[local-name()="chord"]')
        )
        print(f'    M{mi+1}: {len(notes)} notes, beat_total={total:.2f}')
