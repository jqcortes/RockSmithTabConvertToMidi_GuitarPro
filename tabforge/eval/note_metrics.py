"""mir_eval ラッパ（設計書 §12.2 の採譜評価指標）。

onset F1 (±50ms) / onset+pitch F1 を計算する。`mir_eval` は呼び出し時に
のみ import する（`.[eval]` を入れていない環境でも `import` 自体は失敗しない）。
"""
from __future__ import annotations

from dataclasses import dataclass

from tabforge.ir.models import Note

DEFAULT_ONSET_TOLERANCE_SEC = 0.05
DEFAULT_PITCH_TOLERANCE_CENTS = 50.0


@dataclass(frozen=True)
class PrecisionRecallF1:
    precision: float
    recall: float
    f1: float


def _midi_to_hz(pitch: int):
    import numpy as np

    return 440.0 * 2 ** ((np.asarray(pitch, dtype=float) - 69) / 12.0)


def _to_intervals_and_hz(notes: list[Note]):
    import numpy as np

    if not notes:
        return np.zeros((0, 2)), np.zeros((0,))
    intervals = np.array([[n.onset, n.offset] for n in notes], dtype=float)
    pitches_hz = _midi_to_hz(np.array([n.pitch for n in notes]))
    return intervals, pitches_hz


def onset_f1(
    ref: list[Note], est: list[Note], tolerance_sec: float = DEFAULT_ONSET_TOLERANCE_SEC
) -> PrecisionRecallF1:
    """オンセットのみのマッチングによる F1（設計書: onset F1 ±50ms）。"""
    import mir_eval

    ref_intervals, _ = _to_intervals_and_hz(ref)
    est_intervals, _ = _to_intervals_and_hz(est)
    precision, recall, f1 = mir_eval.transcription.onset_precision_recall_f1(
        ref_intervals, est_intervals, onset_tolerance=tolerance_sec
    )
    return PrecisionRecallF1(precision=precision, recall=recall, f1=f1)


def onset_pitch_f1(
    ref: list[Note], est: list[Note],
    onset_tolerance_sec: float = DEFAULT_ONSET_TOLERANCE_SEC,
    pitch_tolerance_cents: float = DEFAULT_PITCH_TOLERANCE_CENTS,
) -> PrecisionRecallF1:
    """オンセット+ピッチのマッチングによる F1（オフセット一致は要求しない）。"""
    import mir_eval

    ref_intervals, ref_hz = _to_intervals_and_hz(ref)
    est_intervals, est_hz = _to_intervals_and_hz(est)
    precision, recall, f1, _avg_overlap = mir_eval.transcription.precision_recall_f1_overlap(
        ref_intervals, ref_hz, est_intervals, est_hz,
        onset_tolerance=onset_tolerance_sec, pitch_tolerance=pitch_tolerance_cents,
        offset_ratio=None,
    )
    return PrecisionRecallF1(precision=precision, recall=recall, f1=f1)
