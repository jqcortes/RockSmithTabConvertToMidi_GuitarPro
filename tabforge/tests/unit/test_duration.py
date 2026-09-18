import pytest

from tabforge.theory.duration import (
    duration_ticks,
    quantize_to_gp_durations,
    seconds_to_ticks,
    ticks_to_seconds,
    to_gp_duration,
)

PPQ = 480


def test_quarter_note():
    d = to_gp_duration(PPQ, PPQ)
    assert (d.value, d.dotted, d.tuplet) == (4, False, None)


def test_eighth_note():
    d = to_gp_duration(PPQ / 2, PPQ)
    assert (d.value, d.dotted, d.tuplet) == (8, False, None)


def test_sixteenth_note():
    d = to_gp_duration(PPQ / 4, PPQ)
    assert (d.value, d.dotted, d.tuplet) == (16, False, None)


def test_thirty_second_note():
    d = to_gp_duration(PPQ / 8, PPQ)
    assert (d.value, d.dotted, d.tuplet) == (32, False, None)


def test_dotted_eighth_is_3_16(): # 付点8分 = 3/16 拍 = 3連符境界の要注意ケース
    dotted_eighth_ticks = duration_ticks(8, PPQ, dotted=True)
    assert dotted_eighth_ticks == pytest.approx(PPQ * 0.75)
    d = to_gp_duration(dotted_eighth_ticks, PPQ)
    assert (d.value, d.dotted, d.tuplet) == (8, True, None)


def test_dotted_quarter():
    dotted_quarter_ticks = duration_ticks(4, PPQ, dotted=True)
    d = to_gp_duration(dotted_quarter_ticks, PPQ)
    assert (d.value, d.dotted, d.tuplet) == (4, True, None)


def test_triplet_eighth():
    # 4分音符の中に3つ = 8分3連
    triplet_ticks = PPQ / 3
    d = to_gp_duration(triplet_ticks, PPQ)
    assert (d.value, d.tuplet) == (8, (3, 2))


def test_quintuplet():
    quint_ticks = duration_ticks(16, PPQ, tuplet=(5, 4))
    d = to_gp_duration(quint_ticks, PPQ)
    assert (d.value, d.tuplet) == (16, (5, 4))


def test_seconds_ticks_round_trip():
    bpm = 132.4
    seconds = 1.2345
    ticks = seconds_to_ticks(seconds, bpm, PPQ)
    back = ticks_to_seconds(ticks, bpm, PPQ)
    assert back == pytest.approx(seconds, abs=1e-3)


def test_unrepresentable_length_splits_with_ties():
    # 4分音符 + 16分音符 相当の半端な長さ（単独 GpDuration では表現不可）
    ticks = duration_ticks(4, PPQ) + duration_ticks(16, PPQ)
    parts = quantize_to_gp_durations(ticks, PPQ)
    assert len(parts) >= 2
    total = sum(duration_ticks(p.value, PPQ, p.dotted, p.tuplet) for p in parts)
    assert total == pytest.approx(ticks, abs=1.0)


def test_exact_length_is_single_duration():
    ticks = duration_ticks(8, PPQ)
    parts = quantize_to_gp_durations(ticks, PPQ)
    assert len(parts) == 1
    assert parts[0].value == 8
