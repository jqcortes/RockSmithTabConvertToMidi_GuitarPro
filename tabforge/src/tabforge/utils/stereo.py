"""ステレオ定位 (pan) 算出（設計書 §7.2 Step6 / 実装指示書 T2-3）。"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfiltfilt

MIN_SEGMENT_SEC = 0.03  # 30ms 未満なら前後にマージンを取る


def _midi_to_hz(pitch: int) -> float:
    return 440.0 * 2 ** ((pitch - 69) / 12.0)


def note_pan(mix_stereo: np.ndarray, sr: int, onset: float, offset: float, pitch: int) -> float:
    """f0 ±1半音の狭帯域 bandpass 後、L/R エネルギー比から pan ∈ [-1,1]。

    区間が 30ms 未満の場合は前後にマージンを取る。無音・不正区間では 0.0 を返す。
    """
    if offset - onset < MIN_SEGMENT_SEC:
        margin = (MIN_SEGMENT_SEC - (offset - onset)) / 2
        onset -= margin
        offset += margin

    start = max(0, int(onset * sr))
    end = min(mix_stereo.shape[0], int(offset * sr))
    if end - start < 8:
        return 0.0

    f0 = _midi_to_hz(pitch)
    low = f0 * 2 ** (-1 / 12)
    high = f0 * 2 ** (1 / 12)
    nyquist = sr / 2
    if high >= nyquist:
        return 0.0
    low = max(low, 1.0)

    sos = butter(4, [low / nyquist, high / nyquist], btype="bandpass", output="sos")
    segment = mix_stereo[start:end]
    left = sosfiltfilt(sos, segment[:, 0])
    right = sosfiltfilt(sos, segment[:, 1])

    left_energy = float(np.sqrt(np.mean(left ** 2)))
    right_energy = float(np.sqrt(np.mean(right ** 2)))
    total = left_energy + right_energy
    if total <= 1e-9:
        return 0.0
    pan = (right_energy - left_energy) / total
    return float(np.clip(pan, -1.0, 1.0))


def attach_pans(notes: list, mix_wav: Path) -> None:
    """Note オブジェクトのリストに pan を破壊的に付与する（fuse Step6 相当）。"""
    import soundfile as sf

    data, sr = sf.read(str(mix_wav), always_2d=True, dtype="float32")
    if data.shape[1] == 1:
        data = np.repeat(data, 2, axis=1)
    for note in notes:
        note.pan = note_pan(data, sr, note.onset, note.offset, note.pitch)
