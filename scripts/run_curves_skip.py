"""
失敗ページ (5, 9, 10, 11) を CURVES スキップ方式で一括変換する。

手順:
  1. Audiveris -step CHORDS -save  →  .omr 保存
  2. .omr の book.xml に CURVES を追記 (patch_omr_skip_curves.py)
  3. Audiveris -transcribe -export  (CURVES をスキップして PAGE まで)

Usage:
  python scripts/run_curves_skip.py [page_nums...]

  page_nums: スペース区切りのページ番号 (例: 5 9 10 11)。
             省略した場合は FAILING_PAGES リストを使う。
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

# このスクリプトからインポートできるようにプロジェクトルートを追加
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.patch_omr_skip_curves import patch_omr  # noqa: E402

# ----- 設定 ---------------------------------------------------------------
JAVA_BIN = Path("C:/Program Files/Audiveris/runtime/bin/java.exe")
CLASSPATH = "C:/Program Files/Audiveris/app/*"
MAIN_CLASS = "Audiveris"
JVM_OPTS = [
    "--enable-native-access=ALL-UNNAMED",
    "--add-exports=java.desktop/sun.awt.image=ALL-UNNAMED",
    "-Xms512m",
]
CONSTANTS = [
    "org.audiveris.omr.sheet.ProcessingSwitches.sixStringTablatures=true",
    "org.audiveris.omr.sheet.ProcessingSwitches.fourStringTablatures=true",
    "org.audiveris.omr.sheet.ProcessingSwitches.fingerings=true",
    "org.audiveris.omr.sheet.ProcessingSwitches.pluckings=true",
    "org.audiveris.omr.sheet.ProcessingSwitches.tremolos=true",
    "org.audiveris.omr.sheet.ProcessingSwitches.articulations=true",
    "org.audiveris.omr.sig.inter.AbstractInter.minGrade=0.35",
]
TIMEOUT_CHORDS = 300   # sec
TIMEOUT_PAGE   = 600   # sec

FAILING_PAGES = [5, 9, 10, 11]

CACHE_DIR = PROJECT_ROOT / ".cache"
# --------------------------------------------------------------------------


def _java_cmd(extra_args: list[str], input_path: Path, output_dir: Path) -> list[str]:
    cmd = [str(JAVA_BIN), "-cp", CLASSPATH] + JVM_OPTS + [MAIN_CLASS]
    cmd += ["-batch"] + extra_args
    for const in CONSTANTS:
        cmd += ["-constant", const]
    cmd += ["-output", str(output_dir)]
    cmd += ["--", str(input_path)]
    return cmd


def _run(cmd: list[str], timeout: int, label: str) -> bool:
    print(f"[RUN] {label}")
    start = time.monotonic()
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    elapsed = time.monotonic() - start
    if result.returncode != 0:
        print(f"[FAIL] {label} (rc={result.returncode}, {elapsed:.1f}s)")
        # 最後の 20 行だけ表示
        lines = (result.stderr + result.stdout).splitlines()
        for l in lines[-20:]:
            print("  ", l)
        return False
    print(f"[OK]   {label} ({elapsed:.1f}s)")
    return True


def process_page(page_num: int) -> bool:
    tag = f"page_{page_num:03d}"
    page_dir = CACHE_DIR / tag
    pre_dir  = page_dir / "preprocess"

    # 前処理済み PNG を探す
    png_files = list(pre_dir.glob("*.png")) if pre_dir.exists() else []
    if not png_files:
        print(f"[SKIP] {tag}: 前処理済み PNG が見つかりません ({pre_dir})")
        return False
    png = png_files[0]

    # ── Step 1: -step CHORDS -save ──────────────────────────────────────────
    chords_dir = page_dir / "omr_chords"
    chords_dir.mkdir(parents=True, exist_ok=True)
    omr_files = list(chords_dir.glob("*.omr"))

    if omr_files:
        omr_path = omr_files[0]
        print(f"[SKIP] {tag} step1: {omr_path.name} が既に存在します")
    else:
        cmd_chords = _java_cmd(
            ["-step", "CHORDS", "-save"],
            input_path=png,
            output_dir=chords_dir,
        )
        ok = _run(cmd_chords, TIMEOUT_CHORDS, f"{tag} step1: -step CHORDS -save")
        if not ok:
            return False
        omr_files = list(chords_dir.glob("*.omr"))
        if not omr_files:
            print(f"[FAIL] {tag}: .omr が生成されませんでした")
            return False
        omr_path = omr_files[0]

    # ── Step 2: book.xml に CURVES を追記 ──────────────────────────────────
    patched = patch_omr(omr_path, ["CURVES"])
    if not patched and "CURVES" not in open_book_xml_steps(omr_path):
        print(f"[FAIL] {tag}: book.xml パッチ失敗")
        return False

    # ── Step 3: -transcribe -export (CURVES 済みとして再開) ────────────────
    mxl_files = list(chords_dir.glob("*.mxl"))
    if mxl_files:
        print(f"[SKIP] {tag} step3: {mxl_files[0].name} が既に存在します")
        return True

    cmd_page = _java_cmd(
        ["-transcribe", "-export"],
        input_path=omr_path,
        output_dir=chords_dir,
    )
    ok = _run(cmd_page, TIMEOUT_PAGE, f"{tag} step3: -transcribe -export")
    if not ok:
        return False

    mxl_files = list(chords_dir.glob("*.mxl"))
    if not mxl_files:
        print(f"[FAIL] {tag}: .mxl が生成されませんでした")
        return False

    print(f"[OUT]  {tag}: {mxl_files[0]}")
    return True


def open_book_xml_steps(omr_path: Path) -> str:
    """book.xml の <steps> の中身を返す（確認用）"""
    import zipfile, re
    with zipfile.ZipFile(omr_path) as zf:
        data = zf.read("book.xml").decode("utf-8")
    m = re.search(r"<steps>(.*?)</steps>", data, re.DOTALL)
    return m.group(1) if m else ""


def main() -> None:
    pages = [int(p) for p in sys.argv[1:]] if len(sys.argv) > 1 else FAILING_PAGES

    results: dict[int, bool] = {}
    for page in pages:
        try:
            results[page] = process_page(page)
        except Exception as exc:
            print(f"[ERROR] page_{page:03d}: {exc}")
            results[page] = False

    print("\n===== 結果 =====")
    for page, ok in results.items():
        status = "✓ OK" if ok else "✗ FAIL"
        print(f"  page_{page:03d}: {status}")

    failed = [p for p, ok in results.items() if not ok]
    sys.exit(0 if not failed else 1)


if __name__ == "__main__":
    main()
