from tabforge.config import TabForgeConfig
from tabforge.ir import io as ir_io
from tabforge.ir.models import NotesIR
from tabforge.job import Job
from tabforge.stages import s0_ingest, s1_separate, s4_transcribe


def test_degrades_to_empty_notes_when_ml_deps_missing(tmp_path, synthetic_riff_wav):
    # このテスト環境には muscriptor/basic-pitch がインストールされていないため、
    # 全ランが degraded になり空の notes_raw.json が書き出されることを確認する。
    job = Job(job_dir=tmp_path / "job", source_audio=synthetic_riff_wav)
    cfg = TabForgeConfig.load(overrides={"separate": {"model": "none"}})
    s0_ingest.Stage().run(job, cfg)
    s1_separate.Stage().run(job, cfg)

    stage = s4_transcribe.Stage()
    assert not stage.is_done(job)
    stage.run(job, cfg)
    assert stage.is_done(job)

    notes = ir_io.load(NotesIR, job.stage_output(stage.name))
    assert notes.notes == []
    assert notes.runs == []
