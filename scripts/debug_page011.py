"""
page_011 を -step CHORDS で実行して STEMS 失敗の原因を調査する。
デバッグログ付きで全ステップを逐次実行する。
"""
import subprocess, sys, os
from pathlib import Path

env_path = r"C:\Program Files\Audiveris\runtime\bin"
os.environ["PATH"] = env_path + ";" + os.environ.get("PATH", "")

JAR    = r"C:\Program Files\Audiveris\app\*"
LB     = str(Path(".").resolve() / "logback-debug.xml")
PNG    = str(Path(".cache/page_011/preprocess").resolve() / "CRASH COMPLEXION_p011.png")
OUT    = str(Path(".cache/page_011/omr_chords").resolve())
LOG_OUT = str(Path(".cache/page_011/omr_chords/debug_stems.log").resolve())

extra_jvm = [
    "--enable-native-access=ALL-UNNAMED",
    "--add-exports=java.desktop/sun.awt.image=ALL-UNNAMED",
    "-Xms512m",
    f"-Dlogback.configurationFile={LB}",
]

cmd = [
    "java", "-cp", JAR,
    *extra_jvm,
    "Audiveris",
    "-batch", "-step", "CHORDS", "-save",
    "-constant", "org.audiveris.omr.sheet.ProcessingSwitches.sixStringTablatures=true",
    "-constant", "org.audiveris.omr.sheet.ProcessingSwitches.fourStringTablatures=true",
    "-constant", "org.audiveris.omr.sig.inter.AbstractInter.minGrade=0.35",
    "-output", OUT,
    "--", PNG,
]
print(f"Running CHORDS step on page_011 (with debug log)...")
result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
combined = result.stdout + "\n" + result.stderr
with open(LOG_OUT, "w", encoding="utf-8", errors="replace") as f:
    f.write(combined)
print(f"Exit: {result.returncode}")

# Show relevant lines
keywords = ["NullPointer", "Exception", "Error", "STEMS", "StemsBuilder", "ERROR"]
shown = 0
for line in combined.splitlines():
    if any(k in line for k in keywords):
        print(line)
        shown += 1
        if shown > 50:
            break
print(f"\nFull log at: {LOG_OUT}")
