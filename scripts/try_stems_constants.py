"""
page_011 の STEMS NPE を回避するため複数の定数の組み合わせを試す。

StemBuilder.getTotalLength() の lengthMap が key=n でヌルポになる。
これは stemScale.getMax()=4 でgapMapが0..4しかないのに、
それ以上のキーが参照されるためと推定。

各試行でログの stem(X max:Y) の Y が変化するか確認する。
"""
import subprocess, sys, os
from pathlib import Path
import zipfile, shutil, re, json

PROJECT_ROOT = Path(__file__).resolve().parent.parent
env_path = r"C:\Program Files\Audiveris\runtime\bin"
os.environ["PATH"] = env_path + ";" + os.environ.get("PATH", "")

JAR      = r"C:\Program Files\Audiveris\app\*"
OMR_ORIG = str(PROJECT_ROOT / ".cache/page_011/omr/CRASH COMPLEXION_p011.omr")
OMR_WORK = str(PROJECT_ROOT / ".cache/page_011/omr_chords/CRASH COMPLEXION_p011.omr")
OUT      = str(PROJECT_ROOT / ".cache/page_011/omr_chords")

BASE_CONSTANTS = [
    ("org.audiveris.omr.sheet.ProcessingSwitches.sixStringTablatures", "true"),
    ("org.audiveris.omr.sheet.ProcessingSwitches.fourStringTablatures", "true"),
    ("org.audiveris.omr.sig.inter.AbstractInter.minGrade", "0.35"),
]

TRIALS = [
    # 試み順に: (説明, 追加定数リスト)
    ("gapHigh_p4=0, p3=0 (reject long-gap stems)",
     [("org.audiveris.omr.sheet.stem.StemChecker.gapHigh_p4", "0.0"),
      ("org.audiveris.omr.sheet.stem.StemChecker.gapHigh_p3", "0.0")]),
    ("lengthHigh=0.5 (short stems only)",
     [("org.audiveris.omr.sheet.stem.StemChecker.lengthHigh", "0.5")]),
    ("maxHeadSeedDy=0.1 (extremely tight head-seed)",
     [("org.audiveris.omr.sheet.stem.StemsRetriever.maxHeadSeedDy", "0.1")]),
    ("maxLinkerLength=0.5 (short linkers only)",
     [("org.audiveris.omr.sheet.stem.StemsRetriever.minLinkerLength", "0.5")]),
]

def run_trial(description, extra_consts):
    shutil.copy2(OMR_ORIG, OMR_WORK)
    constants = BASE_CONSTANTS + extra_consts
    cmd = ["java", "-cp", JAR,
           "--enable-native-access=ALL-UNNAMED",
           "--add-exports=java.desktop/sun.awt.image=ALL-UNNAMED",
           "-Xms512m",
           "Audiveris", "-batch", "-step", "STEMS", "-save"]
    for k, v in constants:
        cmd += ["-constant", f"{k}={v}"]
    cmd += ["-output", OUT, "--", OMR_WORK]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    combined = result.stdout + "\n" + result.stderr
    # stem(X max:Y) を探す
    import re as RE
    stem_match = RE.search(r"stem\((\d+) max:(\d+)\)", combined)
    success = result.returncode == 0
    stem_info = f"stem({stem_match.group(1)} max:{stem_match.group(2)})" if stem_match else "?"
    return success, stem_info

print("Trying multiple constants to fix page_011 STEMS NPE:\n")
for desc, extra in TRIALS:
    ok, stem_info = run_trial(desc, extra)
    status = "✓ SUCCESS" if ok else "✗ FAIL"
    print(f"  {status} | {stem_info} | {desc}")
    if ok:
        print("  → Found working configuration!")
        break
print("\nDone.")
