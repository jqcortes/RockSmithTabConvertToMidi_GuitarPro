"""palm_mute が実際にステム音声から推定され GP5 に反映されることを確認する。"""
from __future__ import annotations

import guitarpro as gp
import numpy as np
import soundfile as sf

from tabforge.cli import _build_stages
from tabforge.config import TabForgeConfig
from tabforge.ir import io as ir_io
from tabforge.ir.models import GridIR, Note, NotesIR, TranscriptionRun
from tabforge.job import Job
from tabforge.stages import s0_ingest, s1_separate, s2_rhythm

SR = 44100


def _tone(freq: float, duration: float, harmonics: int) -> np.ndarray:
    t = np.linspace(0, duration, int(SR * duration), endpoint=False)
    signal = np.zeros_like(t)
    for h in range(1, harmonics + 1):
        signal += (1.0 / h) * np.sin(2 * np.pi * freq * h * t)
    return (signal / np.max(np.abs(signal))).astype(np.float32)


def _bass_notes(grid: GridIR) -> NotesIR:
    # 明るい音(倍音豊富)が続く小節 → 短くくぐもった音が1つ混じる、を模す
    notes = [
        Note(id="n0", onset=grid.beats[0].t, offset=grid.beats[1].t - 0.02, pitch=40,
             instrument="electric_bass", conf=1.0),
        Note(id="n1", onset=grid.beats[1].t, offset=grid.beats[1].t + 0.05, pitch=40,  # 短い(palm mute候補)
             instrument="electric_bass", conf=1.0),
        Note(id="n2", onset=grid.beats[2].t, offset=grid.beats[3].t - 0.02, pitch=40,
             instrument="electric_bass", conf=1.0),
    ]
    return NotesIR(
        runs=[TranscriptionRun(run_id="ms_bass", engine="muscriptor", input="stems/bass.wav",
                                instruments=["electric_bass"])],
        notes=notes,
    )


def test_palm_mute_detected_end_to_end(tmp_path, synthetic_riff_wav):
    job = Job(job_dir=tmp_path / "job", source_audio=synthetic_riff_wav)
    cfg = TabForgeConfig.load(overrides={
        "separate": {"model": "none"},
        "rhythm": {"manual": {"bpm": 120.0, "offset": 0.0, "time_signature": "4/4"}},
    })
    s0_ingest.Stage().run(job, cfg)
    s1_separate.Stage().run(job, cfg)
    s2_rhythm.Stage().run(job, cfg)

    grid = ir_io.load(GridIR, job.stage_output("s2_rhythm"))
    ir_io.save(_bass_notes(grid), job.stage_output("s4_transcribe"))

    # bass.wav ステムを手作りする: n0/n2 = 倍音豊富(明るい), n1 = 基音のみ(くぐもった palm mute)
    beat_len = grid.beats[1].t - grid.beats[0].t
    bright = _tone(82.4, beat_len, harmonics=10)
    muted = _tone(82.4, beat_len, harmonics=1)
    audio = np.concatenate([bright, muted, bright])
    sf.write(job.stems_dir / "bass.wav", audio, SR)

    stages = _build_stages(cfg)
    job.run_pipeline(stages, cfg, from_stage="s4b_fuse", to_stage="s9_export")

    song = gp.parse(str(job.out_path("score.gp5")))
    bass_track = next(t for t in song.tracks if t.name == "Bass")
    all_notes = [n for m in bass_track.measures for v in m.voices for b in v.beats for n in b.notes]
    palm_muted = [n for n in all_notes if n.effect.palmMute]
    assert len(palm_muted) >= 1
