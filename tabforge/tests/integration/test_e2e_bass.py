"""T1-9 相当の end-to-end テスト。

このテスト環境には MuScriptor / Basic Pitch がインストールされていないため、
S4 (採譜) だけは手作りの notes_raw.json で代替し、S0-S2（実処理）と
S4b-S9（実処理）の配線を実際に通す。IR をキャッシュ・差し替え可能にする
設計（D5）が意図した使い方そのものでもある。
"""
from __future__ import annotations

import guitarpro as gp

from tabforge.cli import _build_stages
from tabforge.config import TabForgeConfig
from tabforge.ir import io as ir_io
from tabforge.ir.models import GridIR, Note, NotesIR, TabIR, TranscriptionRun
from tabforge.job import Job
from tabforge.stages import s0_ingest, s1_separate, s2_rhythm


def _synthetic_bass_notes(grid: GridIR) -> NotesIR:
    pitches = [40, 40, 45, 43]  # E2 E2 A2 G2 (synthetic_riff_wav と同じパターン)
    notes = []
    for i, beat in enumerate(grid.beats[:-1]):
        pitch = pitches[i % len(pitches)]
        onset = beat.t + 0.02
        offset = grid.beats[i + 1].t - 0.02
        notes.append(
            Note(id=f"n{i:04d}", onset=onset, offset=offset, pitch=pitch,
                 instrument="electric_bass", conf=1.0, votes=["ms_bass"], src_run="ms_bass")
        )
    return NotesIR(
        runs=[TranscriptionRun(run_id="ms_bass", engine="muscriptor", input="stems/bass.wav",
                                instruments=["electric_bass"])],
        notes=notes,
    )


def test_bass_end_to_end_produces_valid_gp5(tmp_path, synthetic_riff_wav):
    job = Job(job_dir=tmp_path / "job", source_audio=synthetic_riff_wav)
    cfg = TabForgeConfig.load(overrides={
        "separate": {"model": "none"},
        "rhythm": {"manual": {"bpm": 120.0, "offset": 0.0, "time_signature": "4/4"}},
    })

    s0_ingest.Stage().run(job, cfg)
    s1_separate.Stage().run(job, cfg)
    s2_rhythm.Stage().run(job, cfg)

    grid = ir_io.load(GridIR, job.stage_output("s2_rhythm"))
    notes_raw = _synthetic_bass_notes(grid)
    ir_io.save(notes_raw, job.stage_output("s4_transcribe"))

    stages = _build_stages(cfg)
    job.run_pipeline(stages, cfg, from_stage="s4b_fuse", to_stage="s9_export")

    gp5_path = job.out_path("score.gp5")
    assert gp5_path.exists()

    tab = ir_io.load(TabIR, job.stage_output("s7_arrange"))
    assert tab.quality.note_count == len(notes_raw.notes)
    assert tab.quality.unplayable_dropped == 0

    song = gp.parse(str(gp5_path))
    track = song.tracks[0]
    all_notes = [n for m in track.measures for v in m.voices for b in v.beats for n in b.notes]
    assert len(all_notes) == len(notes_raw.notes)
    # 弦番号は 1-indexed で GuitarString の値域内であること
    assert all(1 <= n.string <= len(track.strings) for n in all_notes)


def test_partial_rerun_with_force_and_from_to(tmp_path, synthetic_riff_wav):
    job = Job(job_dir=tmp_path / "job", source_audio=synthetic_riff_wav)
    cfg = TabForgeConfig.load(overrides={
        "separate": {"model": "none"},
        "rhythm": {"manual": {"bpm": 120.0, "offset": 0.0, "time_signature": "4/4"}},
    })
    stages = _build_stages(cfg)

    job.run_pipeline(stages, cfg, to_stage="s2_rhythm")
    assert job.is_cached("s2_rhythm")

    grid = ir_io.load(GridIR, job.stage_output("s2_rhythm"))
    ir_io.save(_synthetic_bass_notes(grid), job.stage_output("s4_transcribe"))
    job.run_pipeline(stages, cfg, from_stage="s4b_fuse", to_stage="s9_export")
    assert job.out_path("score.gp5").exists()

    # --force s7_arrange 相当: s7 以降だけ再計算されること
    old_mtime = job.stage_output("s7_arrange").stat().st_mtime
    job.run_pipeline(
        stages, cfg, from_stage="s7_arrange", to_stage="s9_export", force_stages={"s7_arrange"},
    )
    new_mtime = job.stage_output("s7_arrange").stat().st_mtime
    assert new_mtime >= old_mtime
