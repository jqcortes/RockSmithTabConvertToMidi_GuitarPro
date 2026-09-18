"""共有フィクスチャ。市販楽曲は使わず、自作の短い合成音源のみを使う。"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf


def _sine_riff(sample_rate: int = 44100, bpm: float = 120.0, bars: int = 8) -> np.ndarray:
    """8小節・4分音符ベースラインのごく短い合成音源（メトロノーム相当）。"""
    beat_sec = 60.0 / bpm
    note_pitches_hz = [82.41, 82.41, 110.0, 98.0]  # E2, E2, A2, G2 相当
    samples = []
    for bar in range(bars):
        for beat in range(4):
            freq = note_pitches_hz[beat % len(note_pitches_hz)]
            t = np.linspace(0, beat_sec, int(sample_rate * beat_sec), endpoint=False)
            tone = 0.3 * np.sin(2 * np.pi * freq * t)
            envelope = np.minimum(1.0, np.linspace(0, 20, tone.size)) * np.minimum(
                1.0, np.linspace(20, 0, tone.size) + 1
            )
            samples.append(tone * envelope)
    return np.concatenate(samples).astype(np.float32)


@pytest.fixture
def synthetic_riff_wav(tmp_path: Path) -> Path:
    data = _sine_riff()
    stereo = np.stack([data, data], axis=1)
    path = tmp_path / "riff_8bars.wav"
    sf.write(path, stereo, 44100, subtype="FLOAT")
    return path
