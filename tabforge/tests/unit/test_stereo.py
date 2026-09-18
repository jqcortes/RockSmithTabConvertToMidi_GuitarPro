import numpy as np

from tabforge.utils.stereo import note_pan

SR = 44100


def _tone(freq: float, duration: float) -> np.ndarray:
    t = np.linspace(0, duration, int(SR * duration), endpoint=False)
    return np.sin(2 * np.pi * freq * t).astype(np.float32)


def test_pan_detects_left_channel_dominance():
    tone = _tone(220.0, 0.5)  # A3 = pitch 57
    stereo = np.stack([tone, tone * 0.05], axis=1)
    pan = note_pan(stereo, SR, onset=0.05, offset=0.45, pitch=57)
    assert pan < -0.5


def test_pan_detects_right_channel_dominance():
    tone = _tone(220.0, 0.5)
    stereo = np.stack([tone * 0.05, tone], axis=1)
    pan = note_pan(stereo, SR, onset=0.05, offset=0.45, pitch=57)
    assert pan > 0.5


def test_pan_near_zero_for_centered_signal():
    tone = _tone(220.0, 0.5)
    stereo = np.stack([tone, tone], axis=1)
    pan = note_pan(stereo, SR, onset=0.05, offset=0.45, pitch=57)
    assert abs(pan) < 0.2


def test_short_segment_uses_margin_without_crashing():
    tone = _tone(220.0, 0.5)
    stereo = np.stack([tone, tone], axis=1)
    pan = note_pan(stereo, SR, onset=0.2, offset=0.21, pitch=57)  # 10ms
    assert -1.0 <= pan <= 1.0
