from tabforge.export.report import build_report_context, render_report_html
from tabforge.ir.models import (
    Assignment,
    Beat,
    GridIR,
    Note,
    NotesIR,
    PartsIR,
    TabIR,
    TabMeasure,
    TabTrack,
    TimeSignature,
)

BPM = 120.0
BEAT_LEN = 0.5


def _grid(n_beats: int = 8, warnings=None) -> GridIR:
    beats = [Beat(t=i * BEAT_LEN, beat_in_bar=(i % 4) + 1, bar=i // 4 + 1, is_downbeat=i % 4 == 0,
                   conf=0.9) for i in range(n_beats)]
    return GridIR(sample_rate=44100, duration_sec=n_beats * BEAT_LEN, tempo_bpm_global=BPM,
                  time_signature=TimeSignature(numerator=4, denominator=4), beats=beats,
                  warnings=warnings or [])


def test_report_context_counts_and_unassigned_warning():
    notes = [Note(id=f"n{i}", onset=i * BEAT_LEN, offset=i * BEAT_LEN + 0.4, pitch=64,
                   instrument="guitar", conf=0.9 - i * 0.05) for i in range(4)]
    notes_ir = NotesIR(notes=notes)
    # 4件中2件unassigned = 50% > 5%閾値
    parts = PartsIR(
        assignments=[
            Assignment(note_id="n0", part="lead", score=0.9),
            Assignment(note_id="n1", part="unassigned", score=0.3),
            Assignment(note_id="n2", part="unassigned", score=0.3),
            Assignment(note_id="n3", part="rhythm", score=0.8),
        ],
        part_stats={"lead": 1, "rhythm": 1, "bass": 0, "unassigned": 2},
    )
    grid = _grid()
    tab = TabIR(tracks=[
        TabTrack(name="Bass", part="bass", tuning=[43, 38, 33, 28], string_count=4,
                  measures=[TabMeasure(bar=1, time_signature=(4, 4), tempo=BPM, beats=[])]),
    ])

    ctx = build_report_context(notes_ir, parts, grid, tab)
    assert ctx.total_notes == 4
    assert ctx.part_stats["unassigned"] == 2
    assert any("unassigned" in w for w in ctx.warnings)
    assert ctx.tempo_bpm == BPM
    assert ctx.time_signature == "4/4"
    assert ctx.tracks[0]["name"] == "Bass"


def test_worst_bars_sorted_ascending_by_confidence():
    notes = [
        Note(id="a", onset=0.0, offset=0.4, pitch=64, instrument="guitar", conf=0.9),   # bar1
        Note(id="b", onset=2.0, offset=2.4, pitch=64, instrument="guitar", conf=0.2),   # bar2 (低conf)
    ]
    notes_ir = NotesIR(notes=notes)
    parts = PartsIR(assignments=[], part_stats={"lead": 2, "rhythm": 0, "bass": 0, "unassigned": 0})
    grid = _grid()
    tab = TabIR(tracks=[])

    ctx = build_report_context(notes_ir, parts, grid, tab)
    assert ctx.worst_bars[0][1] < ctx.worst_bars[1][1]


def test_grid_warnings_and_quality_warnings_propagate():
    notes_ir = NotesIR(notes=[])
    parts = PartsIR(assignments=[], part_stats={"lead": 0, "rhythm": 0, "bass": 0, "unassigned": 0})
    grid = _grid(warnings=["bar 3-4: beat confidence < 0.5"])
    tab = TabIR(tracks=[])
    tab.quality.position_jumps_gt5 = 3
    tab.quality.unplayable_dropped = 2

    ctx = build_report_context(notes_ir, parts, grid, tab)
    assert "bar 3-4: beat confidence < 0.5" in ctx.warnings
    assert any("ポジション移動" in w for w in ctx.warnings)
    assert any("破棄された" in w for w in ctx.warnings)


def test_render_report_html_is_valid_looking_document():
    notes_ir = NotesIR(notes=[])
    parts = PartsIR(assignments=[], part_stats={"lead": 0, "rhythm": 0, "bass": 0, "unassigned": 0})
    grid = _grid()
    tab = TabIR(tracks=[])
    ctx = build_report_context(notes_ir, parts, grid, tab)
    doc = render_report_html(ctx)
    assert doc.startswith("<!DOCTYPE html>")
    assert "TabForge Report" in doc
