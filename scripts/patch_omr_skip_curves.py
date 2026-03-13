"""
.omr ファイルの book.xml に指定したステップ名を追記して
Audiveris がそのステップをスキップするようにパッチをあてる。

Usage:
    python scripts/patch_omr_skip_curves.py <path_to_omr> [STEP_NAME ...]

    STEP_NAME: 追記するステップ名。省略した場合は CURVES を追加する。
    例: python scripts/patch_omr_skip_curves.py book.omr STEMS REDUCTION CURVES

パッチ後、同じパス(.omr)を上書きする。
"""

import sys
import zipfile
import shutil
from pathlib import Path
import re


def patch_omr(omr_path: Path, extra_steps: list[str] | None = None) -> bool:
    """book.xml の <steps> に extra_steps を追記する。省略時は CURVES だけ追加。"""
    if extra_steps is None:
        extra_steps = ["CURVES"]

    backup = omr_path.with_suffix(".omr.bak")
    shutil.copy2(omr_path, backup)

    tmp_path = omr_path.with_suffix(".omr.tmp")

    with zipfile.ZipFile(omr_path, "r") as zin:
        with zipfile.ZipFile(tmp_path, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename == "book.xml":
                    xml = data.decode("utf-8")
                    m = re.search(r"<steps>(.*?)</steps>", xml, re.DOTALL)
                    current_steps = m.group(1).strip().split() if m else []
                    to_add = [s for s in extra_steps if s not in current_steps]
                    if not to_add:
                        print(f"[INFO] Steps already present in {omr_path.name}: {extra_steps}")
                        return False
                    new_steps_str = " ".join(current_steps + to_add)
                    xml = re.sub(
                        r"(<steps>)(.*?)(</steps>)",
                        lambda mat: f"{mat.group(1)}{new_steps_str}{mat.group(3)}",
                        xml,
                        flags=re.DOTALL,
                    )
                    data = xml.encode("utf-8")
                    print(f"[INFO] Patched book.xml in {omr_path.name}: added {to_add}")
                zout.writestr(item, data)

    tmp_path.replace(omr_path)
    print(f"[INFO] Saved patched .omr -> {omr_path}")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/patch_omr_skip_curves.py <path.omr> [STEP ...]")
        sys.exit(1)
    path = Path(sys.argv[1])
    steps = sys.argv[2:] if len(sys.argv) > 2 else ["CURVES"]
    if not path.exists():
        print(f"File not found: {path}")
        sys.exit(1)
    ok = patch_omr(path, steps)
    sys.exit(0 if ok else 1)
