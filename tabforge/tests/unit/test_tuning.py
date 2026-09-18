from tabforge.theory.tuning import (
    detect_5string_bass,
    estimate_capo,
    estimate_tuning,
)

GUITAR_STANDARD = (64, 59, 55, 50, 45, 40)  # E4 B3 G3 D3 A2 E2
BASS_STANDARD = (43, 38, 33, 28)  # G2 D2 A1 E1


def test_standard_tuning_detected_when_all_in_range():
    pitches = [60, 62, 64, 65, 67, 69, 71, 72] * 5
    est = estimate_tuning(pitches, GUITAR_STANDARD, "guitar")
    assert est.semitone_shift == 0
    assert not est.drop_lowest
    assert est.out_of_range_rate == 0.0


def test_half_step_down_detected():
    # 大半は Eb2(39) 前後まで下がったフレーズ
    pitches = [39, 41, 43, 44, 46] * 10
    est = estimate_tuning(pitches, GUITAR_STANDARD, "guitar")
    assert est.semitone_shift == 1
    assert not est.drop_lowest


def test_drop_d_detected():
    # 大半は標準域だが、最低弦だけ D2(38) まで使われている
    pitches = [60, 62, 64, 65, 67] * 8 + [38] * 5
    est = estimate_tuning(pitches, GUITAR_STANDARD, "guitar")
    assert est.semitone_shift == 0
    assert est.drop_lowest is True


def test_estimate_capo_suggests_min_fret_when_high():
    frets = [2, 3, 5, 2, 4]
    assert estimate_capo(frets) == 2


def test_estimate_capo_zero_when_open_strings_used():
    frets = [0, 2, 3, 1]
    assert estimate_capo(frets) == 0


def test_detect_5string_bass_true_for_low_extension():
    pitches = [30, 32, 35, 24, 26, 33, 35] * 3  # 24,26 < 28(E1) が有意に存在
    assert detect_5string_bass(pitches) is True


def test_detect_5string_bass_false_for_4string_range():
    pitches = [28, 30, 33, 35, 38, 40, 43] * 3
    assert detect_5string_bass(pitches) is False
