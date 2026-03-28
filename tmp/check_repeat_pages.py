from pathlib import Path
import zipfile
from lxml import etree
from pipeline.render.repeat_expander import RepeatExpander

base = Path('tmp/crash_cache_v3')
pages = [3,4,6,7,8,9,10,11]

for p in pages:
    page_dir = base / f'page_{p:03d}'
    print(f"\n=== PAGE {p:03d} ===")
    if not page_dir.exists():
        print('missing page directory')
        continue

    omr_mxl = page_dir / 'omr' / f'CRASH_COMPLEXION_p{p:03d}.mxl'
    tr_xml = page_dir / 'transform' / f'CRASH_COMPLEXION_p{p:03d}_transformed.xml'

    # OMR source marker counts
    if omr_mxl.exists():
        with zipfile.ZipFile(omr_mxl) as z:
            xml_name = [n for n in z.namelist() if n.lower().endswith('.xml')][0]
            s = z.read(xml_name).decode('utf-8', errors='ignore')
            print('omr markers:', {
                'repeat': s.count('<repeat'),
                'ending': s.count('<ending'),
                'segno': s.count('segno'),
                'coda': s.count('coda'),
                'dacapo': s.count('dacapo'),
                'dalsegno': s.count('dalsegno'),
                'tocoda': s.count('tocoda'),
                'fine': s.count('fine'),
            })
    else:
        print('omr mxl missing')

    if not tr_xml.exists():
        print('transform xml missing')
        continue

    tree = etree.parse(str(tr_xml))
    parts = tree.xpath("//*[local-name()='part']")
    print(f'transform parts={len(parts)}')

    # Transform marker counts
    txt = tr_xml.read_text(encoding='utf-8', errors='ignore')
    print('transform markers:', {
        'repeat': txt.count('<repeat'),
        'ending': txt.count('<ending'),
        'segno': txt.count('segno'),
        'coda': txt.count('coda'),
        'dacapo': txt.count('dacapo'),
        'dalsegno': txt.count('dalsegno'),
        'tocoda': txt.count('tocoda'),
        'fine': txt.count('fine'),
    })

    for part in parts:
        pid = part.get('id', '')
        measures = part.xpath("./*[local-name()='measure']")
        orig_nums = [m.get('number', '?') for m in measures]
        exp = RepeatExpander.expand_part_measures(part)
        exp_nums = [m.get('number', '?') for m in exp.measures]

        # active note count for context
        notes = part.xpath("./*[local-name()='measure']/*[local-name()='note'][not(*[local-name()='rest'])]")
        if len(exp_nums) != len(orig_nums) or exp.warnings:
            print(f" part={pid} notes={len(notes)} original={len(orig_nums)} expanded={len(exp_nums)}")
            print('  original_seq=' + ','.join(orig_nums))
            print('  expanded_seq=' + ','.join(exp_nums))
            if exp.warnings:
                print('  warnings=' + ' | '.join(exp.warnings))
