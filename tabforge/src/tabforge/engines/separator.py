"""Demucs アダプタ（実装指示書 T1-2）。

Python API を直叩きすると torch バージョン競合を招くため、あえて
`python -m demucs` を subprocess で呼ぶ。demucs 未インストールの環境でも
`import tabforge` 自体は失敗しないよう、実行時にのみ確認する。
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path


class SeparatorUnavailable(RuntimeError):
    """demucs がインストールされていない。"""


class Separator:
    def run(
        self,
        mix_wav: Path,
        out_dir: Path,
        model: str = "htdemucs_6s",
        shifts: int = 1,
        overlap: float = 0.25,
        device: str = "cuda",
    ) -> dict[str, Path]:
        """demucs を呼び、stem 名 → wav パスの辞書を返す。

        model="none" の場合は {"mix": mix_wav} を返すだけ（--no-separate）。
        6stem (htdemucs_6s) が失敗したら htdemucs (4stem) にフォールバックする。
        フォールバック時は呼び出し側が `other` を `guitar` として扱うこと
        （設計書 §2.4 / 実装指示書 T1-2）。
        """
        if model == "none":
            return {"mix": mix_wav}

        if importlib.util.find_spec("demucs") is None:
            raise SeparatorUnavailable(
                "demucs がインストールされていません。`pip install -e '.[ml]'` してください。"
            )

        try:
            return self._run_demucs(mix_wav, out_dir, model, shifts, overlap, device)
        except subprocess.CalledProcessError:
            if model == "htdemucs_6s":
                return self._run_demucs(mix_wav, out_dir, "htdemucs", shifts, overlap, device)
            raise

    def _run_demucs(
        self, mix_wav: Path, out_dir: Path, model: str, shifts: int, overlap: float, device: str
    ) -> dict[str, Path]:
        out_dir.mkdir(parents=True, exist_ok=True)
        cmd = [
            sys.executable, "-m", "demucs",
            "-n", model,
            "-o", str(out_dir),
            "--shifts", str(shifts),
            "--overlap", str(overlap),
            "-d", device,
            str(mix_wav),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        stem_dir = out_dir / model / mix_wav.stem
        return {p.stem: p for p in sorted(stem_dir.glob("*.wav"))}
