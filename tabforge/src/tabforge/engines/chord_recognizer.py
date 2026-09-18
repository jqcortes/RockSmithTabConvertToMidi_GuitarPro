"""ChordRecognizer 抽象 + 3実装（設計書 §2.3 / §4.3、実装指示書 T3-1）。

本体は `ChordRecognizer` 抽象クラス越しにしか触らない。LVCR は別コンテナで
プロセス分離する（D6）ため、このプロセス内では常に未実装として扱う。
"""
from __future__ import annotations

from pathlib import Path
from typing import Protocol

from tabforge.ir import io as ir_io
from tabforge.ir.models import ChordsIR


class ChordRecognizerUnavailable(RuntimeError):
    """コード認識エンジンが利用できない（degraded で続行すること）。"""


class ChordRecognizer(Protocol):
    def recognize(self, audio: Path) -> ChordsIR: ...


class ManualJsonRecognizer:
    """人手で書いた chords.json をそのまま読み込む。"""

    def __init__(self, path: Path) -> None:
        self.path = path

    def recognize(self, audio: Path) -> ChordsIR:
        if not self.path.exists():
            raise ChordRecognizerUnavailable(f"manual chords.json が見つからない: {self.path}")
        return ir_io.load(ChordsIR, self.path)


class MadmomRecognizer:
    """フォールバック実装。madmom は任意依存（`.[eval]` 等）で遅延 import する。

    ⚠検証必須: `madmom.features.chords` の実 API（CNNChordFeatureProcessor /
    CRFChordRecognitionProcessor の組み合わせ方）は madmom バージョンに強く
    依存する。ここでは呼び出し口だけ用意し、未インストール時は
    ChordRecognizerUnavailable に正規化する。
    """

    def recognize(self, audio: Path) -> ChordsIR:
        try:
            from madmom.audio.chroma import DeepChromaProcessor
            from madmom.features.chords import (
                CRFChordRecognitionProcessor,
                DeepChromaChordRecognitionProcessor,
            )
        except ImportError as exc:  # pragma: no cover - この環境では常に発生する
            raise ChordRecognizerUnavailable(
                "madmom がインストールされていません。`pip install madmom` してください"
                "（C拡張のビルドに失敗しやすいので注意）。"
            ) from exc

        processor = DeepChromaChordRecognitionProcessor()
        chroma = DeepChromaProcessor()(str(audio))
        annotations = processor(chroma)
        _ = CRFChordRecognitionProcessor  # 将来の切替用に import だけ保持

        segments = [
            {"start": float(start), "end": float(end), "label": str(label)}
            for start, end, label in annotations
        ]
        from tabforge.ir.models import ChordSegment

        return ChordsIR(source="madmom", segments=[ChordSegment(**s) for s in segments])


class LvcrDockerRecognizer:
    """ISMIR2019 LVCR。別コンテナ (docker/Dockerfile.chords) で実行する（D6）。

    インターフェース:
        docker run -v <job_dir>:/job tabforge-chords predict /job/audio/mix.wav /job/ir/chords.json
    コンテナ自体は未実装のプレースホルダのため、常に ChordRecognizerUnavailable を送出する。
    """

    def __init__(self, job_dir: Path) -> None:
        self.job_dir = job_dir

    def recognize(self, audio: Path) -> ChordsIR:
        raise ChordRecognizerUnavailable(
            "LVCR コンテナは未構築（docker/Dockerfile.chords は placeholder）。"
            " chords.recognizer=manual か madmom を使うこと。"
        )
