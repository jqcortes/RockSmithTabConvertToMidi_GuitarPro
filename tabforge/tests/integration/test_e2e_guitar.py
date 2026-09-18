"""T2-4 相当: `--guitar-tracks 1` でギター単一トラックが出力されることを確認する。"""
from __future__ import annotations

import guitarpro as gp

from tabforge.cli import _build_stages
from tabforge.config import TabForgeConfig
from tabforge.ir import io as ir_io
from tabforge.ir.models import GridIR, Note, NotesIR, TabIR, TranscriptionRun
from tabforge.job import Job
from tabforge.stages import s0_ingest, s1_separate, s2_rhythm


def _synthetic_guitar_riff(grid: GridIR) -> NotesIR:
    # E5 パワーコード(12フレット) → G5パワーコード(15フレット) の単純なリフ
    # (S5 Phase A は pitch<45 を bass 扱いするため、低音弦の開放は避ける)
    chord_pairs = [(52, 59), (55, 62)]
    notes = []
    counter = 0
    for i, beat in enumerate(grid.beats[:-1]):
        pitches = chord_pairs[i % len(chord_pairs)]
        onset = beat.t + 0.01
        offset = grid.beats[i + 1].t - 0.01
        for pitch in pitches:
            notes.append(
                Note(id=f"n{counter:04d}", onset=onset, offset=offset, pitch=pitch,
                     instrument="distorted_electric_guitar", conf=1.0,
                     votes=["ms_gtr"], src_run="ms_gtr")
            )
            counter += 1
    return NotesIR(
        runs=[TranscriptionRun(run_id="ms_gtr", engine="muscriptor", input="stems/guitar.wav",
                                instruments=["distorted_electric_guitar"])],
        notes=notes,
    )


def test_guitar_single_track_end_to_end(tmp_path, synthetic_riff_wav):
    job = Job(job_dir=tmp_path / "job", source_audio=synthetic_riff_wav)
    cfg = TabForgeConfig.load(overrides={
        "separate": {"model": "none"},
        "rhythm": {"manual": {"bpm": 120.0, "offset": 0.0, "time_signature": "4/4"}},
        "disentangle": {"guitar_tracks": 1},
    })

    s0_ingest.Stage().run(job, cfg)
    s1_separate.Stage().run(job, cfg)
    s2_rhythm.Stage().run(job, cfg)

    grid = ir_io.load(GridIR, job.stage_output("s2_rhythm"))
    notes_raw = _synthetic_guitar_riff(grid)
    ir_io.save(notes_raw, job.stage_output("s4_transcribe"))

    stages = _build_stages(cfg)
    job.run_pipeline(stages, cfg, from_stage="s4b_fuse", to_stage="s9_export")

    tab = ir_io.load(TabIR, job.stage_output("s7_arrange"))
    names = [t.name for t in tab.tracks]
    assert "Bass" in names
    assert "Guitar" in names

    song = gp.parse(str(job.out_path("score.gp5")))
    guitar_track = next(t for t in song.tracks if t.name == "Guitar")
    all_notes = [n for m in guitar_track.measures for v in m.voices for b in v.beats for n in b.notes]
    assert len(all_notes) == len(notes_raw.notes)
