import xml.etree.ElementTree as ET

tree = ET.parse("tmp/crash_cache_after_fix/page_004/transform/CRASH_COMPLEXION_p004_transformed.xml")
root = tree.getroot()
ns = root.tag.split("}")[0].lstrip("{") if "}" in root.tag else ""

def t(tag):
    return "{" + ns + "}" + tag if ns else tag

notes = root.findall(f".//{t('note')}")
print("Total notes:", len(notes))

pitches = [n for n in notes if n.find(f"{t('pitch')}") is not None]
print("Notes with pitch:", len(pitches))

rests = [n for n in notes if n.find(f"{t('rest')}") is not None]
print("Rests:", len(rests))

# サンプル5件の pitch を表示
for n in pitches[:5]:
    p = n.find(f"{t('pitch')}")
    step = p.find(f"{t('step')}").text
    octave = p.find(f"{t('octave')}").text
    print(f"  {step}/{octave}")

# staff-lines が 6 のパートがあるか
stafflines = root.findall(f".//{t('staff-lines')}")
print("\nstaff-lines values:", [s.text for s in stafflines[:20]])
