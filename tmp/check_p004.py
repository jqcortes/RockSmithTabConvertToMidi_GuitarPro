import xml.etree.ElementTree as ET

tree = ET.parse("tmp/crash_cache_after_fix/page_004/transform/CRASH_COMPLEXION_p004_transformed.xml")
root = tree.getroot()
ns = root.tag.split("}")[0].lstrip("{") if "}" in root.tag else ""

def t(tag):
    return "{" + ns + "}" + tag if ns else tag

parts = root.findall(f".//{t('part-name')}")
print("Parts:", [p.text for p in parts])

notes = root.findall(f".//{t('note')}")
print("Total notes:", len(notes))

tab_notes = [n for n in notes if n.find(f".//{t('technical')}/{t('fret')}") is not None]
print("TAB fret notes:", len(tab_notes))

if tab_notes:
    frets = [int(n.find(f".//{t('technical')}/{t('fret')}").text) for n in tab_notes[:10]]
    strings = [int(n.find(f".//{t('technical')}/{t('string')}").text) for n in tab_notes[:10]]
    print("Sample frets:", frets)
    print("Sample strings:", strings)

# パート名一覧
part_list = root.find(f"{t('part-list')}")
if part_list is not None:
    for sp in part_list.findall(f"{t('score-part')}"):
        pid = sp.get("id")
        pname_el = sp.find(f"{t('part-name')}")
        pname = pname_el.text if pname_el is not None else "?"
        print(f"  part-id={pid}  name={pname}")
