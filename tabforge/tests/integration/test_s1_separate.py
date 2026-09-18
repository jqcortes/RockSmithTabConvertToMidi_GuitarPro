from tabforge.config import TabForgeConfig
from tabforge.job import Job
from tabforge.stages import s0_ingest, s1_separate


def test_no_separate_copies_mix_only(tmp_path, synthetic_riff_wav):
    job = Job(job_dir=tmp_path / "job", source_audio=synthetic_riff_wav)
    cfg = TabForgeConfig.load(overrides={"separate": {"model": "none"}})
    s0_ingest.Stage().run(job, cfg)

    stage = s1_separate.Stage()
    assert not stage.is_done(job)
    stage.run(job, cfg)
    assert stage.is_done(job)
    assert (job.stems_dir / "mix.wav").exists()


def test_degrades_gracefully_when_demucs_missing(tmp_path, synthetic_riff_wav):
    # このテスト環境には demucs がインストールされていないため、
    # 実際に degraded パスを通ることを確認できる。
    job = Job(job_dir=tmp_path / "job", source_audio=synthetic_riff_wav)
    cfg = TabForgeConfig.load()  # デフォルトは htdemucs_6s
    s0_ingest.Stage().run(job, cfg)

    stage = s1_separate.Stage()
    stage.run(job, cfg)
    assert (job.stems_dir / "mix.wav").exists()
