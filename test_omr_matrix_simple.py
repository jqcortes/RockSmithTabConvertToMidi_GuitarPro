#!/usr/bin/env python3
"""
p002のみを6つの設定でテスト（手動実行版）
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

# 各テストケースおよび結果を収集
tests = [
    ("config/test_tab_on_035.properties", "TAB_on", "0.35"),
    ("config/test_tab_on_020.properties", "TAB_on", "0.20"),
    ("config/test_tab_on_010.properties", "TAB_on", "0.10"),
    ("config/test_tab_off_035.properties", "TAB_off", "0.35"),
    ("config/test_tab_off_020.properties", "TAB_off", "0.20"),
    ("config/test_tab_off_010.properties", "TAB_off", "0.10"),
]

results = []

for config_path, tab_label, min_grade in tests:
    print(f"\n{'='*70}")
    print(f"TEST: {tab_label:10} minGrade={min_grade}")
    print(f"{'='*70}")
    
    # キャッシュディレクトリ準備
    test_dir = Path(f"tmp/omr_test_{tab_label}_{min_grade}")
    if test_dir.exists():
        shutil.rmtree(test_dir)
    test_dir.mkdir(parents=True, exist_ok=True)
    
    # 設定を入れ替え
    shutil.copy(config_path, "config/audiveris.properties")
    
    # 変換実行
    cmd = [
        sys.executable, "-m", "pipeline", "convert",
        "--input", "tests/fixtures/CRASH_COMPLEXION.pdf",
        "--output", str(test_dir / "output.mid"),
        "--cache-dir", str(test_dir),
        "--default-role", "guitar",
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        
        if result.returncode == 0:
            # レポートから p002 のみ抽出
            report_path = test_dir / "quality_report.json"
            if report_path.exists():
                with open(report_path) as f:
                    report = json.load(f)
                
                # p002を抽出
                pages = report.get("pages", [])
                p002_data = next((p for p in pages if p.get("page_number") == 2), None)
                
                if p002_data:
                    notes = p002_data["stats"]["total_notes"]
                    measures = p002_data["stats"]["total_measures"]
                    mc = p002_data["metrics"]["measure_completeness"]
                    score = p002_data["overall_score"]
                    judgment = p002_data.get("judgment", "?")
                    
                    result_dict = {
                        "TAB": tab_label,
                        "minGrade": min_grade,
                        "notes": notes,
                        "measures": measures,
                        "MC": round(mc, 4),
                        "score": round(score, 4),
                        "judgment": judgment,
                    }
                    results.append(result_dict)
                    
                    print(f"✓ SUCCESS")
                    print(f"  Notes: {notes} | Measures: {measures}")
                    print(f"  MC: {mc:.4f} | Score: {score:.4f} | Judgment: {judgment}")
                else:
                    print(f"✗ p002 not in report")
            else:
                print(f"✗ quality_report not found")
        else:
            print(f"✗ Conversion failed (code {result.returncode})")
            if result.stderr:
                print(f"  Error: {result.stderr[:200]}")
    except subprocess.TimeoutExpired:
        print(f"✗ TIMEOUT (600s)")
    except Exception as e:
        print(f"✗ Exception: {e}")

# 結果をテーブル形式で表示
print(f"\n{'='*80}")
print(f"RESULTS SUMMARY: p002 only")
print(f"{'='*80}\n")

if results:
    # ヘッダ
    print(f"{'TAB':<10} {'minGrade':<10} {'notes':<8} {'measures':<10} {'MC':<8} {'score':<8} {'judgment':<10}")
    print("-" * 80)
    
    for r in results:
        print(f"{r['TAB']:<10} {r['minGrade']:<10} {r['notes']:<8} {r['measures']:<10} {r['MC']:<8.4f} {r['score']:<8.4f} {r['judgment']:<10}")
    
    # ベスト候補
    print(f"\n{'='*80}")
    print("BEST CANDIDATES:")
    print(f"{'='*80}\n")
    
    best_notes = max(results, key=lambda x: x["notes"])
    best_mc = max(results, key=lambda x: x["MC"])
    best_score = max(results, key=lambda x: x["score"])
    
    print(f"Max notes:  {best_notes['TAB']:10} minGrade={best_notes['minGrade']:5} → {best_notes['notes']} notes")
    print(f"Best MC:    {best_mc['TAB']:10} minGrade={best_mc['minGrade']:5} → MC={best_mc['MC']:.4f}")
    print(f"Best score: {best_score['TAB']:10} minGrade={best_score['minGrade']:5} → {best_score['score']:.4f}")
else:
    print("⚠ No results collected")
