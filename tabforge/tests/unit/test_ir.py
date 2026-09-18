import pytest

from tabforge.ir import io as ir_io
from tabforge.ir.models import (
    Assignment,
    Beat,
    ChordSegment,
    ChordsIR,
    GridIR,
    Note,
    NotesIR,
    PartsIR,
    TabIR,
    TabTrack,
    TimeSignature,
    TranscriptionRun,
)


def _grid() -> GridIR:
    return GridIR(
        sample_rate=44100,
        duration_sec=214.33,
        tempo_bpm_global=132.4,
        time_signature=TimeSignature(numerator=4, denominator=4),
        beats=[Beat(t=0.412, beat_in_bar=1, bar=1, is_downbeat=True, conf=0.93)],
        warnings=["bar 45-47: beat confidence < 0.5"],
    )


def _chords() -> ChordsIR:
    return ChordsIR(
        source="lvcr-ismir2019",
        segments=[
            ChordSegment(
                start=0.41, end=2.23, label="A:min7", root=9, quality="min7",
                bass=9, pitch_classes=[9, 0, 4, 7], conf=0.81,
            )
        ],
    )


def _notes() -> NotesIR:
    return NotesIR(
        runs=[TranscriptionRun(run_id="ms_mix", engine="muscriptor", input="audio/mix.wav")],
        notes=[
            Note(
                id="n000123", onset=12.4123, offset=12.6001, pitch=64,
                instrument="distorted_electric_guitar", conf=0.72,
                votes=["ms_mix"], bend_curve=[(0.0, 0.0), (1.0, 1.05)],
                pan=-0.62, src_run="ms_mix",
            )
        ],
    )


def _parts() -> PartsIR:
    return PartsIR(
        assignments=[Assignment(note_id="n000123", part="lead", score=0.88)],
        part_stats={"lead": 1, "rhythm": 0, "bass": 0, "unassigned": 0},
    )


def _tab() -> TabIR:
    return TabIR(
        tracks=[
            TabTrack(
                name="Lead Guitar", part="lead",
                tuning=[64, 59, 55, 50, 45, 40], string_count=6,
            )
        ]
    )


@pytest.mark.parametrize(
    "factory,model_cls",
    [(_grid, GridIR), (_chords, ChordsIR), (_notes, NotesIR), (_parts, PartsIR), (_tab, TabIR)],
)
def test_round_trip(tmp_path, factory, model_cls):
    model = factory()
    path = tmp_path / "ir.json"
    ir_io.save(model, path)
    loaded = ir_io.load(model_cls, path)
    assert loaded == model


def test_schema_field_is_serialized():
    grid = _grid()
    dumped = grid.model_dump(by_alias=True)
    assert dumped["schema"] == "tabforge.grid/1"
    assert "schema_" not in dumped


def test_schema_version_mismatch_raises(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text('{"schema": "tabforge.grid/999"}', encoding="utf-8")
    with pytest.raises(ir_io.SchemaVersionError):
        ir_io.load(GridIR, path)


def test_missing_schema_field_raises(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(ir_io.SchemaVersionError):
        ir_io.load(GridIR, path)
