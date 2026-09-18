"""T4-2 相当: レガートフレーズで弦跨ぎが発生せず、GP5 に hammer/bend が反映されることを確認する。"""
from __future__ import annotations

import guitarpro as gp

from tabforge.cli import _build_stages
from tabforge.config import TabForgeConfig
from tabforge.ir import io as ir_io
from tabforge.ir.models import GridIR, Note, NotesIR, TranscriptionRun
from tabforge.job import Job
from tabforge.stages import s0_ingest, s1_separate, s2_rhythm


def _hammer_and_bend_phrase(grid: GridIR) -> NotesIR:
    # 32分音符間隔(dt_beats=0.125 < HAMMER_MAX_DT_BEATS=0.25 を確実に満たす)
    thirty_second = (grid.beats[1].t - grid.beats[0].t) / 8
    base = grid.beats[0].t
    notes = [
        # D3(50) -> E3(52) -> F3(53): 同一弦上でのハンマリング想定(隣接、間隔が短い)
        Note(id="h0", onset=base, offset=base + thirty_second, pitch=50,
             instrument="distorted_electric_guitar"),
        Note(id="h1", onset=base + thirty_second, offset=base + 2 * thirty_second, pitch=52,
             instrument="distorted_electric_guitar"),
        Note(id="h2", onset=base + 2 * thirty_second, offset=base + 3 * thirty_second, pitch=53,
             instrument="distorted_electric_guitar"),
        # チョーキングを伴う長めのノート
        Note(id="bend0", onset=base + 4 * thirty_second, offset=base + 4 * thirty_second + 0.4,
             pitch=64, instrument="distorted_electric_guitar",
             bend_curve=[(0.0, 0.0), (0.6, 0.5), (1.0, 1.0)]),
    ]
    return NotesIR(
        runs=[TranscriptionRun(run_id="ms_gtr", engine="muscriptor", input="stems/guitar.wav",
                                instruments=["distorted_electric_guitar"])],
        notes=notes,
    )


def test_hammer_and_bend_survive_full_pipeline(tmp_path, synthetic_riff_wav):
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
    ir_io.save(_hammer_and_bend_phrase(grid), job.stage_output("s4_transcribe"))

    stages = _build_stages(cfg)
    job.run_pipeline(stages, cfg, from_stage="s4b_fuse", to_stage="s9_export")

    song = gp.parse(str(job.out_path("score.gp5")))
    guitar_track = next(t for t in song.tracks if t.name == "Guitar")
    all_notes = [n for m in guitar_track.measures for v in m.voices for b in v.beats for n in b.notes]

    hammer_notes = [n for n in all_notes if n.effect.hammer]
    assert len(hammer_notes) >= 1  # 弦跨ぎせず同一弦上でハンマリングが確定しているはず

    bent_notes = [n for n in all_notes if n.effect.bend is not None]
    assert len(bent_notes) == 1
    last_point = bent_notes[0].effect.bend.points[-1]
    assert (last_point.position, last_point.value) == (12, 4)
