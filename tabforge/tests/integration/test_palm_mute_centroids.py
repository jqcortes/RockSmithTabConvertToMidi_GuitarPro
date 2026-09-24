import numpy as np
import soundfile as sf

from tabforge.ir.models import Note
from tabforge.stages.s8_technique import compute_note_centroids

SR = 44100


def _tone(freq: float, duration: float, harmonics: int = 1) -> np.ndarray:
    t = np.linspace(0, duration, int(SR * duration), endpoint=False)
    signal = np.zeros_like(t)
    for h in range(1, harmonics + 1):
        signal += (1.0 / h) * np.sin(2 * np.pi * freq * h * t)
    return (signal / np.max(np.abs(signal))).astype(np.float32)


def test_muted_segment_has_lower_centroid_than_bright_segment(tmp_path):
    bright = _tone(220.0, 0.5, harmonics=8)  # 倍音豊富 = 重心が高い
    muted = _tone(220.0, 0.5, harmonics=1)   # 基音のみ = 重心が低い
    audio = np.concatenate([bright, muted])
    wav_path = tmp_path / "guitar.wav"
    sf.write(wav_path, audio, SR)

    notes = [
        Note(id="bright", onset=0.0, offset=0.5, pitch=57, instrument="guitar"),
        Note(id="muted", onset=0.5, offset=1.0, pitch=57, instrument="guitar"),
    ]
    centroids = compute_note_centroids(notes, wav_path)
    assert centroids["muted"] < centroids["bright"]


def test_missing_stem_returns_empty_dict(tmp_path):
    notes = [Note(id="a", onset=0.0, offset=0.5, pitch=64, instrument="guitar")]
    centroids = compute_note_centroids(notes, tmp_path / "does_not_exist.wav")
    assert centroids == {}
