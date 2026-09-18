"""P3 完了条件相当: `--guitar-tracks 2` で Lead/Rhythm Guitar + Bass が分かれて出力される。"""
from __future__ import annotations

import guitarpro as gp

from tabforge.cli import _build_stages
from tabforge.config import TabForgeConfig
from tabforge.ir import io as ir_io
from tabforge.ir.models import (
    ChordSegment,
    ChordsIR,
    GridIR,
    Note,
    NotesIR,
    TabIR,
    TranscriptionRun,
)
from tabforge.job import Job
from tabforge.stages import s0_ingest, s1_separate, s2_rhythm


def _synthetic_band_notes(grid: GridIR) -> NotesIR:
    notes = []
    counter = 0
    # 小節1-4: バッキング(3声パワーコード刻み、毎拍)
    for beat_idx in range(16):
        onset = grid.beats[beat_idx].t + 0.01
        offset = grid.beats[beat_idx + 1].t - 0.01
        for pitch in (52, 59, 64):  # E3 B3 E4 見立て
            notes.append(Note(id=f"n{counter:04d}", onset=onset, offset=offset, pitch=pitch,
                               instrument="distorted_electric_guitar", conf=1.0,
                               votes=["ms_gtr"], src_run="ms_gtr"))
            counter += 1
    # 小節5-8: ソロ(16分単音、高音域)
    sixteenth = (grid.beats[1].t - grid.beats[0].t) / 4
    base_t = grid.beats[16].t
    for i in range(64):
        onset = base_t + i * sixteenth
        notes.append(Note(id=f"n{counter:04d}", onset=onset, offset=onset + sixteenth,
                           pitch=76 + (i % 4), instrument="distorted_electric_guitar",
                           conf=1.0, votes=["ms_gtr"], src_run="ms_gtr"))
        counter += 1
    return NotesIR(
        runs=[TranscriptionRun(run_id="ms_gtr", engine="muscriptor", input="stems/guitar.wav",
                                instruments=["distorted_electric_guitar"])],
        notes=notes,
    )


def test_four_track_output_with_guitar_tracks_2(tmp_path, synthetic_riff_wav):
    job = Job(job_dir=tmp_path / "job", source_audio=synthetic_riff_wav)
    cfg = TabForgeConfig.load(overrides={
        "separate": {"model": "none"},
        "rhythm": {"manual": {"bpm": 120.0, "offset": 0.0, "time_signature": "4/4"}},
        "disentangle": {"guitar_tracks": 2},
        "chords": {"recognizer": "manual"},
    })

    s0_ingest.Stage().run(job, cfg)
    s1_separate.Stage().run(job, cfg)
    s2_rhythm.Stage().run(job, cfg)

    grid = ir_io.load(GridIR, job.stage_output("s2_rhythm"))
    ir_io.save(_synthetic_band_notes(grid), job.stage_output("s4_transcribe"))

    manual_chords = ChordsIR(source="manual", segments=[
        ChordSegment(start=0.0, end=grid.beats[16].t, label="E:maj"),
    ])
    ir_io.save(manual_chords, job.job_dir / "chords_manual.json")

    stages = _build_stages(cfg)
    job.run_pipeline(stages, cfg, from_stage="s3_chords", to_stage="s9_export")

    tab = ir_io.load(TabIR, job.stage_output("s7_arrange"))
    names = {t.name for t in tab.tracks}
    assert names == {"Bass", "Lead Guitar", "Rhythm Guitar"}

    song = gp.parse(str(job.out_path("score.gp5")))
    track_names = {t.name for t in song.tracks}
    assert "Lead Guitar" in track_names
    assert "Rhythm Guitar" in track_names

    rhythm_track = next(t for t in song.tracks if t.name == "Rhythm Guitar")
    rhythm_notes = [n for m in rhythm_track.measures for v in m.voices for b in v.beats for n in b.notes]
    assert len(rhythm_notes) > 0
