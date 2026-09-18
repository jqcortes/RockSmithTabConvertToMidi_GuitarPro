from tabforge.arrange.voicing import (
    classify_chord_form,
    generate_candidates,
    generate_strumming,
    select_voicing,
)
from tabforge.ir.models import Beat, ChordSegment, GridIR, Note, TimeSignature

GUITAR_STANDARD = (64, 59, 55, 50, 45, 40)  # E4 B3 G3 D3 A2 E2


def _grid(n_beats: int = 8, bpm: float = 120.0) -> GridIR:
    beat_len = 60.0 / bpm
    beats = [Beat(t=i * beat_len, beat_in_bar=(i % 4) + 1, bar=i // 4 + 1, is_downbeat=i % 4 == 0)
             for i in range(n_beats)]
    return GridIR(sample_rate=44100, duration_sec=n_beats * beat_len, tempo_bpm_global=bpm,
                  time_signature=TimeSignature(numerator=4, denominator=4), beats=beats)


def test_classify_chord_form_power_vs_basic():
    assert classify_chord_form([4, 9]) == "power"       # 2 pitch classes
    assert classify_chord_form([9, 0, 4, 7]) == "basic"  # 4 pitch classes (min7)


def test_power_chord_selected_for_two_note_riff():
    chord = ChordSegment(start=0, end=1, label="E:5", root=4, quality="5", pitch_classes=[4, 11])
    power_notes = [
        Note(id="a", onset=0, offset=0.5, pitch=40, instrument="guitar"),  # E2
        Note(id="b", onset=0, offset=0.5, pitch=47, instrument="guitar"),  # B2
    ]
    shape = select_voicing(chord, power_notes, prev=None, tuning=GUITAR_STANDARD)
    assert shape is not None
    assert shape.quality == "5"


def test_open_e_major_selected_when_root_position_and_matching_sounding():
    chord = ChordSegment(start=0, end=1, label="E:maj", root=4, quality="maj",
                          bass=4, pitch_classes=[4, 8, 11])
    sounding = [
        Note(id="a", onset=0, offset=0.5, pitch=40, instrument="guitar"),
        Note(id="b", onset=0, offset=0.5, pitch=47, instrument="guitar"),
        Note(id="c", onset=0, offset=0.5, pitch=52, instrument="guitar"),
        Note(id="d", onset=0, offset=0.5, pitch=56, instrument="guitar"),
        Note(id="e", onset=0, offset=0.5, pitch=59, instrument="guitar"),
        Note(id="f", onset=0, offset=0.5, pitch=64, instrument="guitar"),
    ]
    shape = select_voicing(chord, sounding, prev=None, tuning=GUITAR_STANDARD)
    assert shape is not None
    assert shape.name == "open"
    assert shape.frets == (0, 0, 1, 2, 2, 0)


def test_slash_chord_excludes_open_shape_and_still_matches_root_quality():
    # D:maj/5 (root=D, bass=A) は分数コードなのでオープンフォーム(root position)は除外される
    chord = ChordSegment(start=0, end=1, label="D:maj/5", root=2, quality="maj",
                          bass=9, pitch_classes=[2, 6, 9])
    shape = select_voicing(chord, [], prev=None, tuning=GUITAR_STANDARD)
    assert shape is not None
    assert shape.name != "open"
    assert shape.quality == "maj"


def test_movement_penalty_prefers_closer_shape():
    chord = ChordSegment(start=0, end=1, label="E:5", root=4, quality="5", pitch_classes=[4, 11])
    from tabforge.arrange.voicing import Shape

    far_prev = Shape(name="prev", root_pc=0, quality="5", frets=(None, None, None, None, 14, 12))
    shape_far = select_voicing(chord, [], prev=far_prev, tuning=GUITAR_STANDARD)
    shape_none = select_voicing(chord, [], prev=None, tuning=GUITAR_STANDARD)
    assert shape_far is not None and shape_none is not None


def test_generate_strumming_alternates_down_up_on_eighth_grid():
    grid = _grid()
    beat_len = 0.5
    notes = [
        Note(id=f"n{i}", onset=i * beat_len / 2, offset=i * beat_len / 2 + 0.1, pitch=64, instrument="guitar")
        for i in range(8)
    ]
    strokes = generate_strumming(notes, grid, subdivisions=2)  # 1拍を2分割 = 8分音符グリッド
    assert len(strokes) == 8
    assert strokes[0].stroke == "down"
    assert strokes[1].stroke == "up"


def test_no_candidates_when_root_missing():
    chord = ChordSegment(start=0, end=1, label="N", pitch_classes=[])
    assert generate_candidates(chord, GUITAR_STANDARD) == []
    assert select_voicing(chord, [], prev=None, tuning=GUITAR_STANDARD) is None
