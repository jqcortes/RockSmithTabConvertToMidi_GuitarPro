from tabforge.config import TabForgeConfig
from tabforge.ir import io as ir_io
from tabforge.ir.models import ChordSegment, ChordsIR
from tabforge.job import Job
from tabforge.stages import s0_ingest, s2_rhythm, s3_chords


def test_degrades_to_no_chord_when_manual_file_missing(tmp_path, synthetic_riff_wav):
    job = Job(job_dir=tmp_path / "job", source_audio=synthetic_riff_wav)
    cfg = TabForgeConfig.load(overrides={
        "rhythm": {"manual": {"bpm": 120.0, "offset": 0.0, "time_signature": "4/4"}},
    })
    s0_ingest.Stage().run(job, cfg)
    s2_rhythm.Stage().run(job, cfg)

    stage = s3_chords.Stage()
    assert not stage.is_done(job)
    stage.run(job, cfg)
    assert stage.is_done(job)

    chords = ir_io.load(ChordsIR, job.stage_output(stage.name))
    assert chords.source == "none"
    assert chords.segments == []


def test_manual_recognizer_reads_and_enriches_chords_json(tmp_path, synthetic_riff_wav):
    job = Job(job_dir=tmp_path / "job", source_audio=synthetic_riff_wav)
    cfg = TabForgeConfig.load(overrides={
        "rhythm": {"manual": {"bpm": 120.0, "offset": 0.0, "time_signature": "4/4"}},
    })
    s0_ingest.Stage().run(job, cfg)
    s2_rhythm.Stage().run(job, cfg)

    manual = ChordsIR(source="manual", segments=[
        ChordSegment(start=0.0, end=4.0, label="A:min7")
    ])
    ir_io.save(manual, job.job_dir / "chords_manual.json")

    stage = s3_chords.Stage()
    stage.run(job, cfg)
    chords = ir_io.load(ChordsIR, job.stage_output(stage.name))
    assert chords.segments[0].root == 9
    assert set(chords.segments[0].pitch_classes) == {9, 0, 4, 7}
