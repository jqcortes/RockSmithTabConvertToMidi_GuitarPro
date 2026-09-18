from tabforge.ir.models import Beat, GridIR, Note, TimeSignature
from tabforge.stages.s6_quantize import quantize_notes

BPM = 120.0
BEAT_LEN = 60.0 / BPM  # 0.5s


def _grid(n_beats: int = 16) -> GridIR:
    beats = [Beat(t=i * BEAT_LEN, beat_in_bar=(i % 4) + 1, bar=i // 4 + 1, is_downbeat=i % 4 == 0)
             for i in range(n_beats)]
    return GridIR(
        sample_rate=44100, duration_sec=n_beats * BEAT_LEN, tempo_bpm_global=BPM,
        time_signature=TimeSignature(numerator=4, denominator=4), beats=beats,
    )


def test_onset_snaps_to_nearest_sixteenth():
    grid = _grid()
    # 2拍目の少し手前(0.49s)に鳴ったノート → 1拍目=0.5s に吸着されるはず
    note = Note(id="a", onset=0.49, offset=0.9, pitch=40, instrument="electric_bass", conf=1.0)
    result = quantize_notes([note], grid)
    assert len(result) == 1
    assert result[0].onset == 0.5


def test_low_confidence_zero_length_note_is_ghost_removed():
    grid = _grid()
    note = Note(id="a", onset=1.001, offset=1.002, pitch=40, instrument="electric_bass", conf=0.1)
    result = quantize_notes([note], grid)
    assert result == []


def test_minimum_note_length_enforced():
    grid = _grid()
    # 極短ノートでも conf が高ければ 32分音符相当の最小長に丸める
    note = Note(id="a", onset=1.0, offset=1.002, pitch=40, instrument="electric_bass", conf=0.9)
    result = quantize_notes([note], grid)
    assert len(result) == 1
    min_len_sec = (BEAT_LEN * 4 / 32)
    assert result[0].offset - result[0].onset >= min_len_sec - 1e-6


def test_quarter_note_length_preserved():
    grid = _grid()
    note = Note(id="a", onset=0.0, offset=BEAT_LEN, pitch=40, instrument="electric_bass", conf=1.0)
    result = quantize_notes([note], grid)
    assert result[0].offset - result[0].onset == BEAT_LEN


def test_exact_duplicates_merged_keeping_higher_confidence():
    grid = _grid()
    notes = [
        Note(id="a", onset=0.0, offset=BEAT_LEN, pitch=40, instrument="electric_bass", conf=0.6),
        Note(id="b", onset=0.01, offset=BEAT_LEN, pitch=40, instrument="electric_bass", conf=0.9),
    ]
    result = quantize_notes(notes, grid)
    assert len(result) == 1
    assert result[0].conf == 0.9
