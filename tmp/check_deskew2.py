import cv2, math, numpy as np
from pathlib import Path
from pipeline.ingest.preprocessor import preprocess

for page in ["p001","p002","p003","p004","p005"]:
    src = Path(f"tmp/crash_cache/ingest/CRASH_COMPLEXION_{page}.png")
    if not src.exists():
        continue
    r = preprocess(src, Path(f"tmp/deskew_test/{page}"))
    print(f"{page}: skew={r.metrics['skew_angle']:.3f}°  warnings={r.warnings}")
