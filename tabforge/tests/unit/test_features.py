from tabforge.ir.models import Beat, ChordSegment, ChordsIR, GridIR, Note, TimeSignature
from tabforge.stages.s5_disentangle import compute_features

BPM = 120.0
BEAT_LEN = 0.5


def _grid(n_beats: int = 16) -> GridIR:
    beats = [Beat(t=i * BEAT_LEN, beat_in_bar=(i % 4) + 1, bar=i // 4 + 1, is_downbeat=i % 4 == 0)
             for i in range(n_beats)]
    return GridIR(sample_rate=44100, duration_sec=n_beats * BEAT_LEN, tempo_bpm_global=BPM,
                  time_signature=TimeSignature(numerator=4, denominator=4), beats=beats)


def _no_chords() -> ChordsIR:
    return ChordsIR(source="none", segments=[])


def test_single_note_sixteenth_run_is_monophonic_and_fast():
    grid = _grid()
    sixteenth = BEAT_LEN / 4
    notes = [
        Note(id=f"n{i}", onset=i * sixteenth, offset=(i + 1) * sixteenth, pitch=64,
             instrument="distorted_electric_guitar")
        for i in range(8)
    ]
    features = compute_features(notes, _no_chords(), grid)
    for note in notes:
        f = features[note.id]
        assert f.poly == 1.0
        assert f.cluster_width == 0.0
        assert f.register == 1.0  # 単音は最上声部扱い
        assert f.dur == 0.25  # 16分 = 0.25拍
    # 2音目以降は ioi が小さい(16分連続)
    assert features["n1"].ioi < 0.5


def test_three_voice_chord_strum_has_high_poly_and_wide_cluster():
    grid = _grid()
    chord_notes = [
        Note(id="a", onset=0.0, offset=0.5, pitch=40, instrument="distorted_electric_guitar"),
        Note(id="b", onset=0.0, offset=0.5, pitch=47, instrument="distorted_electric_guitar"),
        Note(id="c", onset=0.0, offset=0.5, pitch=52, instrument="distorted_electric_guitar"),
    ]
    features = compute_features(chord_notes, _no_chords(), grid)
    for note in chord_notes:
        assert features[note.id].poly == 3.0
    assert features["a"].cluster_width == 12.0  # 52-40
    assert features["a"].register == 0.0  # 最低音
    assert features["c"].register == 1.0  # 最高音


def test_two_note_harmony_has_moderate_cluster_width():
    grid = _grid()
    # 3度ハモリ (長3度=4半音)
    harmony_notes = [
        Note(id="lo", onset=0.0, offset=0.5, pitch=60, instrument="distorted_electric_guitar"),
        Note(id="hi", onset=0.0, offset=0.5, pitch=64, instrument="distorted_electric_guitar"),
    ]
    features = compute_features(harmony_notes, _no_chords(), grid)
    assert features["lo"].poly == 2.0
    assert features["lo"].cluster_width == 4.0
    assert features["lo"].register == 0.0
    assert features["hi"].register == 1.0


def test_chord_tone_scores_high_for_matching_pitch_class():
    grid = _grid()
    chords = ChordsIR(source="manual", segments=[
        ChordSegment(start=0.0, end=4.0, label="C:maj", pitch_classes=[0, 4, 7])
    ])
    matching = Note(id="a", onset=0.5, offset=1.0, pitch=64, instrument="guitar")  # E = pc4, コードトーン
    passing = Note(id="b", onset=1.5, offset=2.0, pitch=66, instrument="guitar")  # F#=pc6, 非和声音寄り
    features = compute_features([matching, passing], chords, grid)
    assert features["a"].chord_tone == 1.0
    assert features["b"].chord_tone < 1.0


def test_bend_extent_reflects_max_deviation():
    grid = _grid()
    note = Note(id="a", onset=0.0, offset=0.5, pitch=64, instrument="guitar",
                bend_curve=[(0.0, 0.0), (0.5, 1.2), (1.0, 0.3)])
    features = compute_features([note], _no_chords(), grid)
    assert features["a"].bend_extent == 1.2
