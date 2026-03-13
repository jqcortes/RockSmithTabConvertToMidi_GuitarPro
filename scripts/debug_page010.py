"""
page_010 を WedgesBuilder/EndingsBuilder デバッグ付きで実行し
CURVES 失敗の詳細ログを取る。
"""
import subprocess, sys
from pathlib import Path

env_path = r"C:\Program Files\Audiveris\runtime\bin"
import os
os.environ["PATH"] = env_path + ";" + os.environ.get("PATH", "")

JAR   = r"C:\Program Files\Audiveris\app\*"
LB    = str(Path(".").resolve() / "logback-debug.xml")
OMR   = str(Path(".cache/page_010/omr_chords/CRASH COMPLEXION_p010.omr").resolve())
OUT   = str(Path(".cache/page_010/omr_debug").resolve())
LOG_OUT = str(Path(".cache/page_010/omr_debug/debug_run.log").resolve())

Path(OUT).mkdir(parents=True, exist_ok=True)

cmd = [
    "java",
    "-cp", JAR,
    "--enable-native-access=ALL-UNNAMED",
    "--add-exports=java.desktop/sun.awt.image=ALL-UNNAMED",
    "-Xms512m",
    f"-Dlogback.configurationFile={LB}",
    "Audiveris",
    "-batch", "-transcribe", "-export",
    "-constant", "org.audiveris.omr.sheet.ProcessingSwitches.sixStringTablatures=true",
    "-constant", "org.audiveris.omr.sheet.ProcessingSwitches.fourStringTablatures=true",
    "-constant", "org.audiveris.omr.sig.inter.AbstractInter.minGrade=0.35",
    "-output", OUT,
    "--", OMR,
]
print(f"Running: java ... Audiveris -batch ...")
result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
combined = result.stdout + "\n" + result.stderr
with open(LOG_OUT, "w", encoding="utf-8", errors="replace") as f:
    f.write(combined)
print(f"Exit: {result.returncode}. Log saved to: {LOG_OUT}")

# Show relevant lines
keywords = ["NullPointer", "Exception", "ERROR", "Error processing", "WedgesBuilder", "EndingsBuilder", "CURVES", "Segments:"]
for line in combined.splitlines():
    if any(k in line for k in keywords):
        print(line)
