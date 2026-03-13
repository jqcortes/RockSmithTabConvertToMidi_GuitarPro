"""
page_011 を sixStringTablatures=false で試す（TAB 優先なしでもノートを取得できるか確認）。
"""
import subprocess, sys, os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
env_path = r"C:\Program Files\Audiveris\runtime\bin"
os.environ["PATH"] = env_path + ";" + os.environ.get("PATH", "")

JAR = r"C:\Program Files\Audiveris\app\*"
OMR = str(PROJECT_ROOT / ".cache/page_011/omr_chords/CRASH COMPLEXION_p011.omr")
OUT = str(PROJECT_ROOT / ".cache/page_011/omr_chords")

cmd = [
    "java", "-cp", JAR,
    "--enable-native-access=ALL-UNNAMED",
    "--add-exports=java.desktop/sun.awt.image=ALL-UNNAMED",
    "-Xms512m",
    "Audiveris",
    "-batch", "-transcribe", "-export",
    # TAB 処理を無効化して STEMS NPE を回避
    "-constant", "org.audiveris.omr.sheet.ProcessingSwitches.sixStringTablatures=false",
    "-constant", "org.audiveris.omr.sheet.ProcessingSwitches.fourStringTablatures=false",
    "-constant", "org.audiveris.omr.sig.inter.AbstractInter.minGrade=0.35",
    "-output", OUT,
    "--", OMR,
]
print("Running with sixStringTablatures=false ...")
result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
print(f"Exit: {result.returncode}")
combined = result.stdout + "\n" + result.stderr
for line in combined.splitlines():
    if any(k in line for k in ["StepMonitoring", "exported", "Error", "WARN", "Exception", "stem("]):
        print(line)

if result.returncode == 0:
    import glob
    mxls = glob.glob(OUT + "/*.mxl")
    print(f"\nMXL files: {mxls}")
