from pathlib import Path
from lxml import etree
from pipeline.render.repeat_expander import RepeatExpander

xml = Path('tmp/crash_cache_v3/page_002/transform/CRASH_COMPLEXION_p002_transformed.xml')
tree = etree.parse(str(xml))
parts = tree.xpath("//*[local-name()='part']")
print(f"xml_exists={xml.exists()} parts={len(parts)}")
for p in parts:
    pid = p.get('id', '')
    measures = p.xpath("./*[local-name()='measure']")
    nums = [m.get('number', '?') for m in measures]
    fwd = sum(1 for m in measures if m.xpath("./*[local-name()='barline']/*[local-name()='repeat'][translate(@direction,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')='forward']"))
    bwd = sum(1 for m in measures if m.xpath("./*[local-name()='barline']/*[local-name()='repeat'][translate(@direction,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')='backward']"))
    endings = sum(1 for m in measures if m.xpath("./*[local-name()='barline']/*[local-name()='ending']"))
    sounds = sum(len(m.xpath(".//*[local-name()='sound'][@dacapo or @dalsegno or @tocoda or @fine]")) for m in measures)
    exp = RepeatExpander.expand_part_measures(p)
    exp_nums = [m.get('number', '?') for m in exp.measures]
    print(f"part={pid} original={len(measures)} expanded={len(exp.measures)} fwd={fwd} bwd={bwd} endings={endings} nav_sounds={sounds}")
    if len(exp_nums) != len(nums):
        print('  expanded_sequence=' + ','.join(exp_nums))
    if exp.warnings:
        print('  warnings=' + ' | '.join(exp.warnings))
