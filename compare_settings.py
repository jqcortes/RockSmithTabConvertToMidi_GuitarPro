import json
notab = json.load(open('tmp/crash_notab/quality_report.json'))['pages'][0]
orig = json.load(open('tmp/crash_cache_v3/page_002/quality_report.json'))
print("=== p002: TAB有 vs TAB無 ===")
print(f"TAB有: {orig['stats']['total_notes']:3d} notes, mc={orig['metrics']['measure_completeness']:.3f}")
print(f"TAB無: {notab['stats']['total_notes']:3d} notes, mc={notab['metrics']['measure_completeness']:.3f}")
diff = notab['stats']['total_notes'] - orig['stats']['total_notes']
pct = diff / orig['stats']['total_notes'] * 100
print(f"Diff: {diff:+d} notes ({pct:+.1f}%)")
