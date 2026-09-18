import soundfile as sf

from tabforge.config import TabForgeConfig
from tabforge.job import Job
from tabforge.stages import s0_ingest


def test_ingest_produces_stereo_and_mono_wav(tmp_path, synthetic_riff_wav):
    job = Job(job_dir=tmp_path / "job", source_audio=synthetic_riff_wav)
    cfg = TabForgeConfig.load()

    stage = s0_ingest.Stage()
    assert not stage.is_done(job)
    stage.run(job, cfg)
    assert stage.is_done(job)

    mix_info = sf.info(job.audio_dir / "mix.wav")
    assert mix_info.samplerate == 44100
    assert mix_info.channels == 2

    mono_info = sf.info(job.audio_dir / "mix_mono.wav")
    assert mono_info.channels == 1
