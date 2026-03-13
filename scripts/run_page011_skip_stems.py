"""
page_011 を STEMS + CURVES スキップで変換する。

page_011 の .omr は既に HEADS まで完了済み（STEMS で NPE が発生するため）。
- STEMS, REDUCTION, CUE_BEAMS, TEXTS, MEASURES, CHORDS, CURVES を book.xml に注入してスキップ
- SYMBOLS → LINKS → RHYTHMS → PAGE まで実行する
"""
import subprocess, sys, os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from scripts.patch_omr_skip_curves import patch_omr  # noqa

env_path = r"C:\Program Files\Audiveris\runtime\bin"
os.environ["PATH"] = env_path + ";" + os.environ.get("PATH", "")

JAR  = r"C:\Program Files\Audiveris\app\*"
OMR  = str(PROJECT_ROOT / ".cache/page_011/omr_chords/CRASH COMPLEXION_p011.omr")
OUT  = str(PROJECT_ROOT / ".cache/page_011/omr_chords")

# スキップするステップ（STEMS から CURVES まで）
SKIP_STEPS = ["STEMS", "REDUCTION", "CUE_BEAMS", "TEXTS", "MEASURES", "CHORDS", "CURVES"]

omr_path = Path(OMR)
print(f"Patching: {omr_path.name}")
patch_omr(omr_path, SKIP_STEPS)

cmd = [
    "java", "-cp", JAR,
    "--enable-native-access=ALL-UNNAMED",
    "--add-exports=java.desktop/sun.awt.image=ALL-UNNAMED",
    "-Xms512m",
    "Audiveris",
    "-batch", "-transcribe", "-export",
    "-constant", "org.audiveris.omr.sheet.ProcessingSwitches.sixStringTablatures=true",
    "-constant", "org.audiveris.omr.sheet.ProcessingSwitches.fourStringTablatures=true",
    "-constant", "org.audiveris.omr.sig.inter.AbstractInter.minGrade=0.35",
    "-output", OUT,
    "--", OMR,
]
print("Running Audiveris -transcribe -export (STEMS through CURVES skipped)...")
result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
combined = result.stdout + "\n" + result.stderr
print(f"Exit: {result.returncode}")

# Show relevant lines
for line in combined.splitlines():
    if any(k in line for k in ["StepMonitoring", "exported", "Error", "WARN", "Exception"]):
        print(line)

if result.returncode == 0:
    mxls = list(Path(OUT).glob("*.mxl"))
    if mxls:
        print(f"\n✓ MXL generated: {mxls[0]}")
    else:
        print("\n? Exit 0 but no MXL found")
