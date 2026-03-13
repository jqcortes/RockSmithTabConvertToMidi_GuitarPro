"""
page_011 を PNG から STEM_SEEDS 定数をカスタマイズして再実行する。
StemScaler の peak detection を調整して gapMap のキー超過を防ぐ。
"""
import subprocess, sys, os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
env_path = r"C:\Program Files\Audiveris\runtime\bin"
os.environ["PATH"] = env_path + ";" + os.environ.get("PATH", "")

JAR = r"C:\Program Files\Audiveris\app\*"
PNG = str(PROJECT_ROOT / ".cache/page_011/preprocess/CRASH COMPLEXION_p011.png")
OUT = str(PROJECT_ROOT / ".cache/page_011/omr_stems_fix")

Path(OUT).mkdir(parents=True, exist_ok=True)

# StemScaler constants:
# minValueRatio: Absolute ratio of total pixels for peak acceptance (default ~0.004?)
# minDerivativeRatio: For strong derivative
# minGainRatio: Minimum ratio for stem peak extension
TRIALS = [
    ("minValueRatio=0.01",
     [("org.audiveris.omr.sheet.stem.StemScaler.minValueRatio", "0.01")]),
    ("minValueRatio=0.02",
     [("org.audiveris.omr.sheet.stem.StemScaler.minValueRatio", "0.02")]),
    ("minValueRatio=0.005",
     [("org.audiveris.omr.sheet.stem.StemScaler.minValueRatio", "0.005")]),
    ("stemAsForeRatio=0.9 (very high foreground threshold)",
     [("org.audiveris.omr.sheet.stem.StemScaler.stemAsForeRatio", "0.9")]),
]

BASE_CONSTANTS = [
    ("org.audiveris.omr.sheet.ProcessingSwitches.sixStringTablatures", "true"),
    ("org.audiveris.omr.sheet.ProcessingSwitches.fourStringTablatures", "true"),
    ("org.audiveris.omr.sig.inter.AbstractInter.minGrade", "0.35"),
]

def run_trial(description, extra_consts, timeout=300):
    trial_out = str(Path(OUT) / description.replace(" ", "_").replace("=", ""))
    Path(trial_out).mkdir(parents=True, exist_ok=True)
    cmd = ["java", "-cp", JAR,
           "--enable-native-access=ALL-UNNAMED",
           "--add-exports=java.desktop/sun.awt.image=ALL-UNNAMED",
           "-Xms512m",
           "Audiveris", "-batch", "-step", "CHORDS", "-save"]
    for k, v in BASE_CONSTANTS + extra_consts:
        cmd += ["-constant", f"{k}={v}"]
    cmd += ["-output", trial_out, "--", PNG]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    combined = result.stdout + "\n" + result.stderr
    import re
    stem_m = re.search(r"stem\((\d+) max:(\d+)\)", combined)
    stem_info = f"stem({stem_m.group(1)} max:{stem_m.group(2)})" if stem_m else "?"
    success = result.returncode == 0
    return success, stem_info

print("Trying StemScaler constants from PNG for page_011:\n")
for desc, extra in TRIALS:
    print(f"  Testing: {desc} ...", end="", flush=True)
    ok, stem_info = run_trial(desc, extra)
    status = "✓ SUCCESS" if ok else "✗ FAIL"
    print(f"\r  {status} | {stem_info} | {desc}")
    if ok:
        print("  → Found working configuration!")
        import glob
        mxls = glob.glob(str(Path(OUT) / "*" / "*.mxl"))
        print(f"  MXL: {mxls}")
        break
print("\nDone.")
