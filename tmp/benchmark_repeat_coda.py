from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
CONFIG_TARGET = ROOT / "config" / "audiveris.properties"
BACKUP = ROOT / "tmp" / "audiveris.properties.bak"

TESTS = [
    ("config/test_tab_on_035.properties", "TAB_on_035"),
    ("config/test_tab_on_020.properties", "TAB_on_020"),
    ("config/test_tab_on_010.properties", "TAB_on_010"),
    ("config/test_tab_off_035.properties", "TAB_off_035"),
    ("config/test_tab_off_020.properties", "TAB_off_020"),
    ("config/test_tab_off_010.properties", "TAB_off_010"),
]

# User-relevant pages from the repeat/coda discussion.
PAGES = [3, 4, 6, 7, 8, 9, 10, 11]
PAGES_ARG = ",".join(str(p) for p in PAGES)

KEYS = ["<repeat", "<ending", "segno", "coda", "dacapo", "dalsegno", "tocoda", "fine"]


def read_mxl_counts(mxl_path: Path) -> dict[str, int]:
    with zipfile.ZipFile(mxl_path) as zf:
        xml_name = next(name for name in zf.namelist() if name.lower().endswith(".xml"))
        text = zf.read(xml_name).decode("utf-8", errors="ignore")
    return {k: text.count(k) for k in KEYS}


def main() -> int:
    ROOT.joinpath("tmp").mkdir(exist_ok=True)
    if CONFIG_TARGET.exists():
        shutil.copy2(CONFIG_TARGET, BACKUP)

    all_results: list[dict[str, object]] = []

    try:
        for cfg_rel, label in TESTS:
            cfg = ROOT / cfg_rel
            cache_dir = ROOT / "tmp" / f"repeat_coda_bench_{label}"
            out_mid = ROOT / "tmp" / f"repeat_coda_bench_{label}.mid"
            if cache_dir.exists():
                shutil.rmtree(cache_dir)
            if out_mid.exists():
                out_mid.unlink()

            shutil.copy2(cfg, CONFIG_TARGET)

            cmd = [
                str(PYTHON),
                "-m",
                "pipeline",
                "convert",
                "--input",
                "tests/fixtures/CRASH_COMPLEXION.pdf",
                "--pages",
                PAGES_ARG,
                "--output",
                str(out_mid),
                "--cache-dir",
                str(cache_dir),
                "--default-role",
                "guitar",
            ]
            proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)

            per_page: dict[str, object] = {}
            totals = {k: 0 for k in KEYS}
            ok_pages = 0

            for p in PAGES:
                mxl = cache_dir / f"page_{p:03d}" / "omr" / f"CRASH_COMPLEXION_p{p:03d}.mxl"
                if mxl.exists():
                    counts = read_mxl_counts(mxl)
                    per_page[f"p{p:03d}"] = counts
                    ok_pages += 1
                    for k in KEYS:
                        totals[k] += counts[k]
                else:
                    per_page[f"p{p:03d}"] = None

            all_results.append(
                {
                    "label": label,
                    "config": cfg_rel,
                    "returncode": proc.returncode,
                    "ok_pages": ok_pages,
                    "target_pages": len(PAGES),
                    "totals": totals,
                    "per_page": per_page,
                    "stderr_tail": proc.stderr[-1000:] if proc.stderr else "",
                }
            )

            print(
                f"{label}: rc={proc.returncode} ok_pages={ok_pages}/{len(PAGES)} "
                f"repeat={totals['<repeat']} ending={totals['<ending']} coda={totals['coda']}"
            )

        summary_path = ROOT / "tmp" / "repeat_coda_benchmark_summary.json"
        summary_path.write_text(json.dumps(all_results, ensure_ascii=False, indent=2), encoding="utf-8")

        ranked = sorted(
            all_results,
            key=lambda r: (
                int(r["ok_pages"]),
                int(r["totals"]["<repeat"]),
                int(r["totals"]["coda"]),
                int(r["totals"]["segno"]),
                -int(r["returncode"]),
            ),
            reverse=True,
        )

        print("\n=== Ranked (ok_pages, repeat, coda, segno) ===")
        for r in ranked:
            t = r["totals"]
            print(
                f"{r['label']}: ok={r['ok_pages']}/{r['target_pages']} "
                f"repeat={t['<repeat']} coda={t['coda']} segno={t['segno']} "
                f"ending={t['<ending']} rc={r['returncode']}"
            )

        print(f"\nSaved: {summary_path}")
        return 0
    finally:
        if BACKUP.exists():
            shutil.copy2(BACKUP, CONFIG_TARGET)


if __name__ == "__main__":
    raise SystemExit(main())
