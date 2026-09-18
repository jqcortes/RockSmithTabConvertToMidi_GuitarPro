"""Basic Pitch アダプタ（実装指示書 T1-4 / 設計書 §2.2）。

⚠検証必須: `note_events` のタプル構造・`pitch_bend` の値域は
`basic-pitch` の実バージョンで確認すること。ここでは公開ドキュメント記載の
`(start_time_s, end_time_s, pitch_midi, amplitude, pitch_bend)` を想定する。
"""
from __future__ import annotations

from pathlib import Path

from tabforge.ir.models import Note


class BasicPitchUnavailable(RuntimeError):
    """basic-pitch がインストールされていない。"""


class BasicPitchEngine:
    def __init__(
        self,
        onset_threshold: float = 0.5,
        frame_threshold: float = 0.3,
        minimum_note_length: float = 58,
        multiple_pitch_bends: bool = True,
        minimum_frequency: float | None = None,
        maximum_frequency: float | None = None,
        melodia_trick: bool = False,
    ) -> None:
        self.onset_threshold = onset_threshold
        self.frame_threshold = frame_threshold
        self.minimum_note_length = minimum_note_length
        self.multiple_pitch_bends = multiple_pitch_bends
        self.minimum_frequency = minimum_frequency
        self.maximum_frequency = maximum_frequency
        self.melodia_trick = melodia_trick

    def transcribe(self, audio: Path, instrument: str, run_id: str) -> list[Note]:
        try:
            from basic_pitch.inference import predict
        except ImportError as exc:  # pragma: no cover - この環境では常に発生する
            raise BasicPitchUnavailable(
                "basic-pitch がインストールされていません。`pip install -e '.[ml]'` してください。"
            ) from exc

        _model_output, _midi_data, note_events = predict(
            str(audio),
            onset_threshold=self.onset_threshold,
            frame_threshold=self.frame_threshold,
            minimum_note_length=self.minimum_note_length,
            minimum_frequency=self.minimum_frequency,
            maximum_frequency=self.maximum_frequency,
            multiple_pitch_bends=self.multiple_pitch_bends,
            melodia_trick=self.melodia_trick,
        )

        notes: list[Note] = []
        for i, event in enumerate(note_events):
            start_time, end_time, pitch, amplitude, pitch_bend = event
            bend_curve = _to_bend_curve(pitch_bend)
            notes.append(
                Note(
                    id=f"{run_id}_{i:06d}",
                    onset=float(start_time),
                    offset=float(end_time),
                    pitch=round(pitch),
                    instrument=instrument,
                    conf=float(amplitude),
                    votes=[run_id],
                    bend_curve=bend_curve,
                    src_run=run_id,
                )
            )
        return notes


def _to_bend_curve(pitch_bend) -> list[tuple[float, float]] | None:
    """basic-pitch のフレーム単位ベンド配列を [(相対位置0-1, セミトーン偏差), ...] に変換する。"""
    if pitch_bend is None:
        return None
    values = list(pitch_bend)
    if not values:
        return None
    n = len(values)
    return [(i / max(1, n - 1), float(v)) for i, v in enumerate(values)]
