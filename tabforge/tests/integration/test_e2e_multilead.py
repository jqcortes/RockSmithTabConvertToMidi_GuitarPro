"""T3-5 相当: `--guitar-tracks 3` で複数リードトラックに K-means 分割される。"""
from __future__ import annotations

import guitarpro as gp

from tabforge.cli import _build_stages
from tabforge.config import TabForgeConfig
from tabforge.ir import io as ir_io
from tabforge.ir.models import GridIR, Note, NotesIR, TabIR, TranscriptionRun
from tabforge.job import Job
from tabforge.stages import s0_ingest, s1_separate, s2_rhythm


def _two_solo_lines(grid: GridIR) -> NotesIR:
    sixteenth = (grid.beats[1].t - grid.beats[0].t) / 4
    notes = []
    counter = 0
    # 高音域ソロ(前半, 左寄り)
    for i in range(32):
        onset = grid.beats[0].t + i * sixteenth
        notes.append(Note(id=f"n{counter:04d}", onset=onset, offset=onset + sixteenth,
                           pitch=76 + (i % 3), instrument="distorted_electric_guitar",
                           conf=1.0, votes=["ms_gtr"], src_run="ms_gtr", pan=-0.6))
        counter += 1
    # 別の高音域ソロ(後半, 右寄り)、時間帯を分けてクラスタが混ざらないようにする
    base_t = grid.beats[8].t
    for i in range(32):
        onset = base_t + i * sixteenth
        notes.append(Note(id=f"n{counter:04d}", onset=onset, offset=onset + sixteenth,
                           pitch=79 + (i % 3), instrument="distorted_electric_guitar",
                           conf=1.0, votes=["ms_gtr"], src_run="ms_gtr", pan=0.6))
        counter += 1
    return NotesIR(
        runs=[TranscriptionRun(run_id="ms_gtr", engine="muscriptor", input="stems/guitar.wav",
                                instruments=["distorted_electric_guitar"])],
        notes=notes,
    )


def test_guitar_tracks_3_splits_lead_by_pan(tmp_path, synthetic_riff_wav):
    job = Job(job_dir=tmp_path / "job", source_audio=synthetic_riff_wav)
    cfg = TabForgeConfig.load(overrides={
        "separate": {"model": "none"},
        "rhythm": {"manual": {"bpm": 120.0, "offset": 0.0, "time_signature": "4/4"}},
        "disentangle": {"guitar_tracks": 3},
    })
    s0_ingest.Stage().run(job, cfg)
    s1_separate.Stage().run(job, cfg)
    s2_rhythm.Stage().run(job, cfg)

    grid = ir_io.load(GridIR, job.stage_output("s2_rhythm"))
    ir_io.save(_two_solo_lines(grid), job.stage_output("s4_transcribe"))

    stages = _build_stages(cfg)
    job.run_pipeline(stages, cfg, from_stage="s4b_fuse", to_stage="s9_export")

    tab = ir_io.load(TabIR, job.stage_output("s7_arrange"))
    names = {t.name for t in tab.tracks}
    assert "Bass" in names
    lead_track_names = names - {"Bass"}
    assert len(lead_track_names) >= 2  # 複数リードトラックに分かれている

    song = gp.parse(str(job.out_path("score.gp5")))
    gp_names = {t.name for t in song.tracks}
    assert lead_track_names <= gp_names
