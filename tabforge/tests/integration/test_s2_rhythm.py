import pytest

from tabforge.config import TabForgeConfig
from tabforge.ir import io as ir_io
from tabforge.ir.models import GridIR
from tabforge.job import Job
from tabforge.stages import s0_ingest, s2_rhythm


def test_manual_bpm_bypasses_estimation(tmp_path, synthetic_riff_wav):
    job = Job(job_dir=tmp_path / "job", source_audio=synthetic_riff_wav)
    cfg = TabForgeConfig.load(
        overrides={"rhythm": {"manual": {"bpm": 120.0, "offset": 0.0, "time_signature": "4/4"}}}
    )
    s0_ingest.Stage().run(job, cfg)

    stage = s2_rhythm.Stage()
    assert not stage.is_done(job)
    stage.run(job, cfg)
    assert stage.is_done(job)

    grid = ir_io.load(GridIR, job.stage_output(stage.name))
    assert grid.tempo_bpm_global == 120.0
    assert grid.time_signature.numerator == 4
    assert grid.beats[0].is_downbeat
    assert grid.beats[4].is_downbeat  # 4/4 なので5拍目もダウンビート


@pytest.mark.slow
def test_librosa_estimation_runs_on_synthetic_riff(tmp_path, synthetic_riff_wav):
    job = Job(job_dir=tmp_path / "job", source_audio=synthetic_riff_wav)
    cfg = TabForgeConfig.load()
    s0_ingest.Stage().run(job, cfg)

    stage = s2_rhythm.Stage()
    stage.run(job, cfg)
    grid = ir_io.load(GridIR, job.stage_output(stage.name))
    assert grid.tempo_bpm_global > 0
    assert len(grid.beats) > 0
