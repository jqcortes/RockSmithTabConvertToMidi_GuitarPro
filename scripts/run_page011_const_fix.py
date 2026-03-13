"""
page_011 を maxHeadSeedDy を小さくして STEMS NPE を回避する試み。
"""
import subprocess, sys, os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

env_path = r"C:\Program Files\Audiveris\runtime\bin"
os.environ["PATH"] = env_path + ";" + os.environ.get("PATH", "")

JAR  = r"C:\Program Files\Audiveris\app\*"

# HEADS 状態の .omr を元のバッチ run から使用
OMR_SRC = str(PROJECT_ROOT / ".cache/page_011/omr/CRASH COMPLEXION_p011.omr")
OMR_DST = str(PROJECT_ROOT / ".cache/page_011/omr_chords/CRASH COMPLEXION_p011.omr")
OUT  = str(PROJECT_ROOT / ".cache/page_011/omr_chords")

import shutil, zipfile, re
# もし omr_chords の .omr が HEADS 状態でなければ omr/ のものを使う
def get_steps(path):
    try:
        with zipfile.ZipFile(path) as z:
            xml = z.read("book.xml").decode("utf-8")
        m = re.search(r"<steps>(.*?)</steps>", xml, re.DOTALL)
        return m.group(1).strip() if m else ""
    except Exception:
        return ""

src_steps = get_steps(OMR_SRC)
dst_steps = get_steps(OMR_DST)
print(f"omr/ steps:        {src_steps}")
print(f"omr_chords/ steps: {dst_steps}")

# HEADS 状態の .omr を使う
if "STEMS" not in src_steps and "HEADS" in src_steps:
    shutil.copy2(OMR_SRC, OMR_DST)
    print("Restored clean HEADS .omr")

cmd = [
    "java", "-cp", JAR,
    "--enable-native-access=ALL-UNNAMED",
    "--add-exports=java.desktop/sun.awt.image=ALL-UNNAMED",
    "-Xms512m",
    "Audiveris",
    "-batch", "-step", "CHORDS", "-save",
    "-constant", "org.audiveris.omr.sheet.ProcessingSwitches.sixStringTablatures=true",
    "-constant", "org.audiveris.omr.sheet.ProcessingSwitches.fourStringTablatures=true",
    "-constant", "org.audiveris.omr.sig.inter.AbstractInter.minGrade=0.35",
    # 試み: maxHeadSeedDy を減らして長すぎるステムを早期排除
    "-constant", "org.audiveris.omr.sheet.stem.StemsRetriever.maxHeadSeedDy=1.5",
    "-output", OUT,
    "--", OMR_DST,
]
print("Running CHORDS with maxHeadSeedDy=1.5 ...")
result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
combined = result.stdout + "\n" + result.stderr
print(f"Exit: {result.returncode}")
for line in combined.splitlines():
    if any(k in line for k in ["StepMonitoring", "Error", "WARN", "stem(", "Exception"]):
        print(line)

if result.returncode == 0:
    import glob
    omrs = glob.glob(OUT + "/*.omr")
    if omrs:
        steps = get_steps(omrs[0])
        print(f"Result .omr steps: {steps}")
