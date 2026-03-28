#!/usr/bin/env python3
"""
OMR マトリックステスト（クイック版）
- キャッシュを再利用して高速化
- p002 のメトリクスのみを抽出
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

# Test configurations
tests = [
    ("config/test_tab_on_035.properties", "TAB_on", "0.35"),
    ("config/test_tab_on_020.properties", "TAB_on", "0.20"),
    ("config/test_tab_on_010.properties", "TAB_on", "0.10"),
    ("config/test_tab_off_035.properties", "TAB_off", "0.35"),
    ("config/test_tab_off_020.properties", "TAB_off", "0.20"),
    ("config/test_tab_off_010.properties", "TAB_off", "0.10"),
]

results = []
base_cache = Path("tmp/omr_test_cache")

for config_path, tab_label, min_grade in tests:
    print(f"\n{'='*70}")
    print(f"TEST: {tab_label:10} minGrade={min_grade}")
    print(f"{'='*70}")
    
    # テスト用キャッシュ
    test_cache = base_cache / f"{tab_label}_{min_grade}"
    
    # 既存キャッシュをリセット（前のテストアーティファクト削除）
    if test_cache.exists():
        for item in test_cache.iterdir():
            if item.is_dir() and item.name.startswith("page_"):
                shutil.rmtree(item)
    
    test_cache.mkdir(parents=True, exist_ok=True)
    
    # 設定をコピー
    shutil.copy(config_path, "config/audiveris.properties")
    
    # 変換実行（出力は捨てる）
    cmd = [
        sys.executable, "-m", "pipeline", "convert",
        "--input", "tests/fixtures/CRASH_COMPLEXION.pdf",
        "--output", str(test_cache / "output.mid"),
        "--cache-dir", str(test_cache),
        "--default-role", "guitar",
    ]
    
    try:
        # stderr を redirects、stdout を無視して UI をすっきり
        result = subprocess.run(cmd, timeout=900, capture_output=True, text=True)
        
        if result.returncode == 0:
            report_path = test_cache / "quality_report.json"
            if report_path.exists():
                with open(report_path) as f:
                    report = json.load(f)
                
                pages = report.get("pages", [])
                p002_data = next((p for p in pages if p.get("page_number") == 2), None)
                
                if p002_data:
                    notes = p002_data["stats"]["total_notes"]
                    measures = p002_data["stats"]["total_measures"]
                    mc = p002_data["metrics"]["measure_completeness"]
                    score = p002_data["overall_score"]
                    judgment = p002_data.get("judgment", "?")
                    
                    results.append({
                        "TAB": tab_label,
                        "minGrade": min_grade,
                        "notes": notes,
                        "measures": measures,
                        "MC": round(mc, 4),
                        "score": round(score, 4),
                        "judgment": judgment,
                    })
                    
                    print(f"✓ SUCCESS")
                    print(f"  Notes: {notes:3d} | Measures: {measures:2d} | "
                          f"MC: {mc:.4f} | Score: {score:.4f} | {judgment}")
                else:
                    print(f"✗ p002 not found in report")
            else:
                print(f"✗ quality_report.json missing")
        else:
            print(f"✗ Conversion failed (code {result.returncode})")
            if result.stderr:
                print(f"  stderr: {result.stderr[:300]}")
    except subprocess.TimeoutExpired:
        print(f"✗ TIMEOUT (900s)")
    except Exception as e:
        print(f"✗ Exception: {type(e).__name__}: {e}")

# Print summary table
print(f"\n{'='*90}")
print(f"RESULTS SUMMARY (p002 only)")
print(f"{'='*90}\n")

if not results:
    print("No successful results!")
    sys.exit(1)

# Header
print(f"{'TAB':<10} {'minGrade':<10} {'Notes':<8} {'Meas':<6} {'MC':<10} {'Score':<10} {'Judgment':<15}")
print("-" * 90)

# Data rows
best_mc = max(r["MC"] for r in results)
best_score = max(r["score"] for r in results)

for r in results:
    mc_marker = "★" if r["MC"] == best_mc else " "
    score_marker = "★" if r["score"] == best_score else " "
    print(f"{r['TAB']:<10} {r['minGrade']:<10} {r['notes']:<8} {r['measures']:<6} "
          f"{mc_marker}{r['MC']:<9.4f} {score_marker}{r['score']:<9.4f} {r['judgment']:<15}")

print("\n★ = Best in category")
print(f"\nBest MC: {best_mc} (measure_completeness)")
print(f"Best Score: {best_score} (overall_score)")
