from lxml import etree

t = etree.parse('tmp/crash_cache_v3/page_007/transform/CRASH_COMPLEXION_p007_transformed.xml')
parts = t.xpath("//*[local-name()='part-list']/*[local-name()='score-part']")
for p in parts:
    pid = p.get('id')
    name = ''.join(p.xpath("./*[local-name()='part-name']/text()"))
    print(pid, name)
