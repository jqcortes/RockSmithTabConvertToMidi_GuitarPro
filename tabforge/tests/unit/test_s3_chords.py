from tabforge.ir.models import Beat, ChordSegment, ChordsIR, GridIR, TimeSignature
from tabforge.stages.s3_chords import align_segments_to_grid, enrich_pitch_classes

BPM = 120.0
BEAT_LEN = 0.5


def _grid(n_beats: int = 16) -> GridIR:
    beats = [Beat(t=i * BEAT_LEN, beat_in_bar=(i % 4) + 1, bar=i // 4 + 1, is_downbeat=i % 4 == 0)
             for i in range(n_beats)]
    return GridIR(sample_rate=44100, duration_sec=n_beats * BEAT_LEN, tempo_bpm_global=BPM,
                  time_signature=TimeSignature(numerator=4, denominator=4), beats=beats)


def test_enrich_pitch_classes_fills_missing_fields():
    chords = ChordsIR(source="manual", segments=[ChordSegment(start=0, end=1, label="A:min7")])
    enriched = enrich_pitch_classes(chords)
    assert enriched.segments[0].root == 9
    assert set(enriched.segments[0].pitch_classes) == {9, 0, 4, 7}


def test_enrich_skips_segments_that_already_have_pitch_classes():
    chords = ChordsIR(source="manual", segments=[
        ChordSegment(start=0, end=1, label="C:maj", pitch_classes=[0, 4, 7])
    ])
    enriched = enrich_pitch_classes(chords)
    assert enriched.segments[0].root is None  # 上書きされない


def test_segments_snap_to_nearest_beat():
    grid = _grid()
    chords = ChordsIR(source="manual", segments=[
        ChordSegment(start=0.48, end=1.99, label="C:maj"),  # 0.5s, 2.0s に吸着されるはず
    ])
    aligned = align_segments_to_grid(chords, grid, min_segment_beats=1.0)
    assert aligned.segments[0].start == 0.5
    assert aligned.segments[0].end == 2.0


def test_short_segment_absorbed_into_previous():
    grid = _grid()
    chords = ChordsIR(source="manual", segments=[
        ChordSegment(start=0.0, end=2.0, label="C:maj"),
        ChordSegment(start=2.0, end=2.2, label="D:maj"),  # 1拍未満(0.5s) -> 吸収される
        ChordSegment(start=2.5, end=4.0, label="G:maj"),
    ])
    aligned = align_segments_to_grid(chords, grid, min_segment_beats=1.0)
    assert len(aligned.segments) == 2
    assert aligned.segments[0].label == "C:maj"
    assert aligned.segments[0].end == 2.2  # D:maj の区間が C:maj に吸収され延長
    assert aligned.segments[1].label == "G:maj"
