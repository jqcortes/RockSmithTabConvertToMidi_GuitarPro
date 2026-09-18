from tabforge.config import FusionConfig
from tabforge.ir.models import Note, NotesIR, TranscriptionRun
from tabforge.stages.s4b_fuse import fuse, match_and_vote, remove_octave_errors

WEIGHTS = {"ms_mix": 1.0, "ms_bass": 0.8, "bp_bass": 0.5}


def _note(id_, onset, offset, pitch, src_run, conf=1.0) -> Note:
    return Note(id=id_, onset=onset, offset=offset, pitch=pitch, instrument="electric_bass",
                conf=conf, votes=[src_run], src_run=src_run)


def test_duplicate_notes_across_runs_merge_into_one():
    notes = [
        _note("a", 1.00, 1.50, 40, "ms_mix"),
        _note("b", 1.02, 1.48, 40, "ms_bass"),   # ほぼ同一区間・同ピッチ → IoU 高
        _note("c", 1.01, 1.49, 40, "bp_bass"),
    ]
    merged = match_and_vote(notes, WEIGHTS, iou_threshold=0.5)
    assert len(merged) == 1
    assert set(merged[0].votes) == {"ms_mix", "ms_bass", "bp_bass"}
    assert merged[0].conf == WEIGHTS["ms_mix"] + WEIGHTS["ms_bass"] + WEIGHTS["bp_bass"]


def test_ms_mix_only_note_kept_with_low_confidence():
    notes = [_note("a", 2.0, 2.5, 45, "ms_mix")]
    merged = match_and_vote(notes, WEIGHTS, iou_threshold=0.5)
    assert len(merged) == 1
    assert merged[0].votes == ["ms_mix"]
    assert merged[0].conf == WEIGHTS["ms_mix"]


def test_bp_only_note_is_discarded():
    notes = [
        _note("a", 1.0, 1.5, 40, "ms_mix"),
        _note("b", 5.0, 5.5, 50, "bp_bass"),  # ms_mix に対応が無い単独ノート
    ]
    merged = match_and_vote(notes, WEIGHTS, iou_threshold=0.5)
    assert len(merged) == 1
    assert merged[0].pitch == 40


def test_low_iou_does_not_merge():
    notes = [
        _note("a", 1.0, 1.5, 40, "ms_mix"),
        _note("b", 1.4, 2.4, 40, "ms_bass"),  # 重なりは小さい (IoU < 0.5)
    ]
    merged = match_and_vote(notes, WEIGHTS, iou_threshold=0.5)
    assert len(merged) == 1
    assert merged[0].votes == ["ms_mix"]


def test_octave_error_removed_when_nested_and_low_score():
    fundamental = Note(id="f", onset=1.0, offset=2.0, pitch=40, instrument="bass",
                        conf=1.8, votes=["ms_mix", "ms_bass"])
    octave_ghost = Note(id="g", onset=1.1, offset=1.6, pitch=52, instrument="bass",
                         conf=0.5, votes=["bp_bass"])
    cleaned = remove_octave_errors([fundamental, octave_ghost])
    assert [n.id for n in cleaned] == ["f"]


def test_octave_error_kept_when_score_close():
    fundamental = Note(id="f", onset=1.0, offset=2.0, pitch=40, instrument="bass", conf=1.0)
    octave_double = Note(id="g", onset=1.1, offset=1.6, pitch=52, instrument="bass", conf=0.9)
    cleaned = remove_octave_errors([fundamental, octave_double])
    assert {n.id for n in cleaned} == {"f", "g"}


def test_fuse_end_to_end_returns_notes_ir():
    raw = NotesIR(
        runs=[TranscriptionRun(run_id="ms_mix", engine="muscriptor", input="mix.wav")],
        notes=[
            _note("a", 1.0, 1.5, 40, "ms_mix"),
            _note("b", 1.0, 1.5, 40, "ms_bass"),
        ],
    )
    result = fuse(raw, FusionConfig())
    assert isinstance(result, NotesIR)
    assert len(result.notes) == 1
    assert result.runs == raw.runs
