import numpy as np

from tabforge.export.auralize import synthesize
from tabforge.ir.models import GpDuration, TabBeat, TabIR, TabMeasure, TabNote, TabTrack

BASS_TUNING = [43, 38, 33, 28]


def test_synthesize_produces_nonzero_signal_of_expected_length():
    measures = [
        TabMeasure(bar=1, time_signature=(4, 4), tempo=120.0, beats=[
            TabBeat(start_tick=0, duration=GpDuration(value=4), notes=[TabNote(string=4, fret=0)]),
            TabBeat(start_tick=0, duration=GpDuration(value=4), notes=[TabNote(string=3, fret=2)]),
        ]),
    ]
    tab = TabIR(tracks=[TabTrack(name="Bass", part="bass", tuning=BASS_TUNING,
                                  string_count=4, measures=measures)])
    sr = 44100
    signal = synthesize(tab, sample_rate=sr)

    # 2つの4分音符(120bpm=0.5s each) = 合計1.0秒相当
    expected_samples = int(1.0 * sr)
    assert abs(len(signal) - expected_samples) < sr * 0.05
    assert np.max(np.abs(signal)) > 0.0


def test_synthesize_empty_tab_returns_minimal_signal():
    tab = TabIR(tracks=[])
    signal = synthesize(tab)
    assert len(signal) >= 1
    assert np.all(signal == 0.0)
