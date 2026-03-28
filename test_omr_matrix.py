#!/usr/bin/env python3
"""
OMR設定マトリックステスト：p002 のみを複数の設定で変換
"""
import json
import shutil
import subprocess
import time
from pathlib import Path

TEST_CASES = [
    ("test_tab_on_035", "TAB on", "0.35"),
    ("test_tab_on_020", "TAB on", "0.20"),
    ("test_tab_on_010", "TAB on", "0.10"),
    ("test_tab_off_035", "TAB off", "0.35"),
    ("test_tab_off_020", "TAB off", "0.20"),
    ("test_tab_off_010", "TAB off", "0.10"),
]

BASE_CACHE_DIR = Path("tmp/omr_matrix_test")
BASE_CACHE_DIR.mkdir(exist_ok=True)

results = []

for config_name, tab_status, min_grade in TEST_CASES:
    print(f"\n{'='*60}")
    print(f"TEST: {config_name} ({tab_status}, minGrade={min_grade})")
    print(f"{'='*60}")
    
    # キャッシュクリア
    test_cache = BASE_CACHE_DIR / config_name
    if test_cache.exists():
        shutil.rmtree(test_cache)
    test_cache.mkdir(parents=True, exist_ok=True)
    output_dir = test_cache / "output"
    output_dir.mkdir(exist_ok=True)
    
    # 設定ファイル入れ替え
    config_file = Path(f"config/{config_name}.properties")
    shutil.copy(config_file, "config/audiveris.properties")
    print(f"✓ Config: {config_file}")
    
    start = time.time()
    try:
        # 変換実行（全ページ、p002のみ)
        result = subprocess.run(
            [
                "python", "-m", "pipeline", "convert",
                "--input", "tests/fixtures/CRASH_COMPLEXION.pdf",
                "--output", str(output_dir / "output.mid"),
                "--cache-dir", str(test_cache),
                "--default-role", "guitar",
            ],
            capture_output=True,
            text=True,
            timeout=600,
        )
        elapsed = time.time() - start
        
        if result.returncode == 0:
            # レポート読込
            report_path = output_dir / "quality_report.json"
            if report_path.exists():
                with open(report_path) as f:
                    report = json.load(f)
                
                # 全ページの統計
                pages = report.get("pages", [])
                # p002を抽出（ページ番号2）
                p002 = next((p for p in pages if p.get("page_number") == 2), None)
                
                if p002:
                    stats = p002.get("stats", {})
                    metrics = p002.get("metrics", {})
                    notes = stats.get("total_notes", 0)
                    measures = stats.get("total_measures", 0)
                    mc = metrics.get("measure_completeness", 0)
                    score = p002.get("overall_score", 0)
                else:
                    # p002がない場合は全体統計を使用
                    stats = report.get("stats", {})
                    metrics = report.get("metrics", {})
                    notes = stats.get("total_notes", 0)
                    measures = stats.get("total_measures", 0)
                    mc = metrics.get("measure_completeness", 0)
                    score = report.get("overall_score", 0)
                
                result_row = {
                    "config": config_name,
                    "tab": tab_status,
                    "minGrade": min_grade,
                    "OMR_time": f"{elapsed:.1f}s",
                    "total_notes": notes,
                    "total_measures": measures,
                    "measure_completeness": f"{mc:.3f}",
                    "overall_score": f"{score:.3f}",
                }
                results.append(result_row)
                
                print(f"✓ Success (OMR: {elapsed:.1f}s)")
                print(f"  Notes: {notes} | Measures: {measures} | MC: {mc:.3f} | Score: {score:.3f}")
            else:
                print(f"✗ No quality report found")
        else:
            print(f"✗ Conversion failed: {result.returncode}")
            if result.stderr:
                print(f"  StdErr: {result.stderr[:200]}")
    except subprocess.TimeoutExpired:
        print(f"✗ Timeout (600s exceeded)")
    except Exception as e:
        print(f"✗ Error: {e}")

# 結果集計
print(f"\n{'='*80}")
print("MATRIX TEST RESULTS")
print(f"{'='*80}\n")

if results:
    # ヘッダ
    print(f"{'Config':<20} {'TAB':<10} {'minGrade':<10} {'OMR Time':<10} {'Notes':<10} {'MC':<8} {'Score':<8}")
    print("-" * 80)
    
    for r in results:
        print(f"{r['config']:<20} {r['tab']:<10} {r['minGrade']:<10} {r['OMR_time']:<10} {r['total_notes']:<10} {r['measure_completeness']:<8} {r['overall_score']:<8}")
    
    # 最適候補
    print(f"\n{'BEST CANDIDATES'}")
    print("-" * 80)
    
    # ノート数最大
    best_notes = max(results, key=lambda x: x["total_notes"])
    print(f"Most notes: {best_notes['config']} ({best_notes['total_notes']} notes)")
    
    # MC最高
    best_mc = max(results, key=lambda x: float(x["measure_completeness"]))
    print(f"Best MC: {best_mc['config']} ({best_mc['measure_completeness']})")
    
    # スコア最高
    best_score = max(results, key=lambda x: float(x["overall_score"]))
    print(f"Best score: {best_score['config']} ({best_score['overall_score']})")
else:
    print("⚠ No results collected")
