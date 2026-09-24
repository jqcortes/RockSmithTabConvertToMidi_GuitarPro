import math

from tabforge.config import TechniqueConfig
from tabforge.ir.models import Note
from tabforge.stages.s8_technique import (
    confirm_hammer_or_slide,
    infer_bend,
    infer_dead_note,
    infer_let_ring,
    infer_palm_mute,
    infer_vibrato,
    is_legato_candidate,
)


def _note(id_="a", onset=0.0, offset=0.5, pitch=64, bend_curve=None) -> Note:
    return Note(id=id_, onset=onset, offset=offset, pitch=pitch, instrument="guitar",
                bend_curve=bend_curve)


def test_bend_detected_when_deviation_large_and_rises_in_second_half():
    note = _note(bend_curve=[(0.0, 0.0), (0.6, 0.5), (1.0, 1.0)])
    effect = infer_bend(note, TechniqueConfig())
    assert effect is not None
    assert effect.points[-1] == (12, 4)  # position=1.0*12=12, value=1.0*4=4(1半音)


def test_bend_not_detected_when_deviation_small():
    note = _note(bend_curve=[(0.0, 0.0), (1.0, 0.3)])  # < 0.7半音(既定閾値)
    assert infer_bend(note, TechniqueConfig()) is None


def test_bend_not_detected_when_rises_in_first_half():
    # 最大偏差が前半にある(=チョーキングの typical な形ではない)
    note = _note(bend_curve=[(0.1, 1.0), (0.9, 0.1)])
    assert infer_bend(note, TechniqueConfig()) is None


def test_bend_disabled_by_config():
    note = _note(bend_curve=[(0.0, 0.0), (1.0, 1.0)])
    cfg = TechniqueConfig(enabled={**TechniqueConfig().enabled, "bend": False})
    assert infer_bend(note, cfg) is None


def _vibrato_curve(freq_hz: float, amplitude: float, duration: float, n: int = 40) -> list[tuple[float, float]]:
    return [
        (i / (n - 1), amplitude * math.sin(2 * math.pi * freq_hz * (i / (n - 1)) * duration))
        for i in range(n)
    ]


def test_vibrato_detected_for_typical_rate_and_amplitude():
    note = _note(onset=0.0, offset=1.0, bend_curve=_vibrato_curve(freq_hz=6.0, amplitude=0.4, duration=1.0))
    assert infer_vibrato(note, TechniqueConfig()) is True


def test_vibrato_not_detected_when_too_fast():
    note = _note(onset=0.0, offset=1.0, bend_curve=_vibrato_curve(freq_hz=20.0, amplitude=0.4, duration=1.0))
    assert infer_vibrato(note, TechniqueConfig()) is False


def test_vibrato_not_detected_when_amplitude_too_small():
    note = _note(onset=0.0, offset=1.0, bend_curve=_vibrato_curve(freq_hz=6.0, amplitude=0.05, duration=1.0))
    assert infer_vibrato(note, TechniqueConfig()) is False


def test_legato_candidate_true_for_close_fast_notes():
    prev = _note(pitch=60)
    cur = _note(pitch=62)
    assert is_legato_candidate(prev, cur, dt_beats=0.2) is True


def test_legato_candidate_false_when_too_far_apart_in_pitch():
    prev = _note(pitch=40)
    cur = _note(pitch=70)
    assert is_legato_candidate(prev, cur, dt_beats=0.1) is False


def test_confirm_hammer_when_same_string_close_fret_and_fast():
    hammer, slide = confirm_hammer_or_slide(dt_beats=0.1, fret_diff=2, same_string=True, cfg=TechniqueConfig())
    assert hammer is True
    assert slide is None


def test_confirm_slide_when_same_string_wider_fret_and_slower():
    hammer, slide = confirm_hammer_or_slide(dt_beats=0.4, fret_diff=3, same_string=True, cfg=TechniqueConfig())
    assert hammer is False
    assert slide == "shiftSlideTo"


def test_confirm_none_when_different_string():
    hammer, slide = confirm_hammer_or_slide(dt_beats=0.1, fret_diff=2, same_string=False, cfg=TechniqueConfig())
    assert hammer is False
    assert slide is None


def test_dead_note_for_very_short_duration():
    note = _note(onset=1.0, offset=1.03)
    assert infer_dead_note(note, TechniqueConfig()) is True


def test_dead_note_false_for_normal_duration():
    note = _note(onset=1.0, offset=1.5)
    assert infer_dead_note(note, TechniqueConfig()) is False


def test_let_ring_when_overlapping_next_onset_and_enabled():
    note = _note(onset=0.0, offset=1.0)
    nxt = _note(id_="b", onset=0.8, offset=1.5)
    cfg = TechniqueConfig(enabled={**TechniqueConfig().enabled, "let_ring": True})
    assert infer_let_ring(note, nxt, cfg) is True


def test_let_ring_disabled_by_default():
    note = _note(onset=0.0, offset=1.0)
    nxt = _note(id_="b", onset=0.8, offset=1.5)
    assert infer_let_ring(note, nxt, TechniqueConfig()) is False  # 既定 OFF


def test_palm_mute_true_when_short_and_dark():
    note = _note(onset=0.0, offset=0.1)  # 短い(拍長0.5秒なら0.2拍)
    result = infer_palm_mute(note, dt_beats_duration=0.2, centroid=500.0,
                              track_median_centroid=1000.0, cfg=TechniqueConfig())
    assert result is True


def test_palm_mute_false_when_not_short():
    note = _note(onset=0.0, offset=1.0)
    result = infer_palm_mute(note, dt_beats_duration=0.9, centroid=500.0,
                              track_median_centroid=1000.0, cfg=TechniqueConfig())
    assert result is False


def test_palm_mute_false_when_centroid_not_dark_enough():
    note = _note(onset=0.0, offset=0.1)
    result = infer_palm_mute(note, dt_beats_duration=0.2, centroid=900.0,
                              track_median_centroid=1000.0, cfg=TechniqueConfig())
    assert result is False


def test_palm_mute_false_when_centroid_missing():
    note = _note(onset=0.0, offset=0.1)
    result = infer_palm_mute(note, dt_beats_duration=0.2, centroid=None,
                              track_median_centroid=1000.0, cfg=TechniqueConfig())
    assert result is False
