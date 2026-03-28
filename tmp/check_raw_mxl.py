import zipfile
import xml.etree.ElementTree as ET

# 生 MXL を展開して TAB 関連要素を探す
with zipfile.ZipFile("tmp/crash_cache_after_fix/page_004/omr/CRASH_COMPLEXION_p004.mxl") as zf:
    xml_name = [n for n in zf.namelist() if n.endswith(".xml")][0]
    with zf.open(xml_name) as f:
        content = f.read().decode("utf-8")

tree = ET.fromstring(content)
ns = tree.tag.split("}")[0].lstrip("{") if "}" in tree.tag else ""
def t(tag): return "{" + ns + "}" + tag if ns else tag

# staff-lines
sl = tree.findall(f".//{t('staff-lines')}")
print("staff-lines:", [e.text for e in sl])

# clef sign
clefs = tree.findall(f".//{t('sign')}")
print("clef signs:", [e.text for e in clefs])

# part-name
pnames = tree.findall(f".//{t('part-name')}")
print("part-names:", [e.text for e in pnames])

# instrument-name
inames = tree.findall(f".//{t('instrument-name')}")
print("instrument-names:", [e.text for e in inames])

# fret 要素
frets = tree.findall(f".//{t('fret')}")
print("fret elements:", len(frets), [e.text for e in frets[:5]])

# notes with technical
technicals = tree.findall(f".//{t('technical')}")
print("technical elements:", len(technicals))

# midi-program
progs = tree.findall(f".//{t('midi-program')}")
print("midi-programs:", [e.text for e in progs])
