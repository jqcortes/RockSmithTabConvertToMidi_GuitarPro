"""tests for pipeline CLI entrypoint."""

from __future__ import annotations

import json
from pathlib import Path

from mido import Message, MetaMessage, MidiFile, MidiTrack

from pipeline.common import IngestError, StepResult


def _write_test_midi(path: Path, note: int) -> None:
    midi_file = MidiFile(type=1, ticks_per_beat=480)

    meta_track = MidiTrack()
    meta_track.append(MetaMessage("set_tempo", tempo=500000, time=0))
    meta_track.append(MetaMessage("end_of_track", time=0))
    midi_file.tracks.append(meta_track)

    note_track = MidiTrack()
    note_track.append(Message("program_change", channel=0, program=29, time=0))
    note_track.append(Message("note_on", channel=0, note=note, velocity=64, time=0))
    note_track.append(Message("note_off", channel=0, note=note, velocity=0, time=480))
    note_track.append(MetaMessage("end_of_track", time=0))
    midi_file.tracks.append(note_track)

    midi_file.save(path)


def test_main_convert_runs_full_pipeline_and_returns_pass(monkeypatch, tmp_path: Path) -> None:
    from pipeline import __main__ as cli

    input_path = tmp_path / "score.png"
    input_path.write_bytes(b"png")
    output_path = tmp_path / "song.mid"

    preprocessed = tmp_path / "preprocessed.png"
    musicxml = tmp_path / "score.musicxml"
    transformed = tmp_path / "score_transformed.xml"
    rendered = tmp_path / "score_transformed.mid"
    rendered.write_bytes(b"MThd")

    monkeypatch.setattr(cli, "load", lambda *_args, **_kwargs: StepResult.ok([input_path]))
    monkeypatch.setattr(cli, "preprocess", lambda *_args, **_kwargs: StepResult.ok(preprocessed))
    monkeypatch.setattr(cli, "validate", lambda *_args, **_kwargs: StepResult.ok(preprocessed))
    monkeypatch.setattr(cli, "transcribe", lambda *_args, **_kwargs: StepResult.ok(musicxml))
    monkeypatch.setattr(cli, "transform", lambda *_args, **_kwargs: StepResult.ok(transformed))
    monkeypatch.setattr(cli, "render", lambda *_args, **_kwargs: StepResult.ok(rendered))
    monkeypatch.setattr(
        cli,
        "score",
        lambda *_args, **_kwargs: StepResult.ok(
            tmp_path / "quality_report.json",
            metrics={"judgment": "PASS", "overall_score": 0.9},
        ),
    )

    exit_code = cli.main(["convert", "--input", str(input_path), "--output", str(output_path)])

    assert exit_code == 0
    assert output_path.exists()
    assert output_path.read_bytes() == b"MThd"


def test_main_convert_maps_review_and_fail_to_exit_codes(monkeypatch, tmp_path: Path) -> None:
    from pipeline import __main__ as cli

    input_path = tmp_path / "score.png"
    input_path.write_bytes(b"png")
    output_path = tmp_path / "song.mid"
    rendered = tmp_path / "rendered.mid"
    rendered.write_bytes(b"MThd")

    monkeypatch.setattr(cli, "load", lambda *_args, **_kwargs: StepResult.ok([input_path]))
    monkeypatch.setattr(cli, "preprocess", lambda *_args, **_kwargs: StepResult.ok(tmp_path / "pre.png"))
    monkeypatch.setattr(cli, "validate", lambda *_args, **_kwargs: StepResult.ok(tmp_path / "pre.png"))
    monkeypatch.setattr(cli, "transcribe", lambda *_args, **_kwargs: StepResult.ok(tmp_path / "out.xml"))
    monkeypatch.setattr(cli, "transform", lambda *_args, **_kwargs: StepResult.ok(tmp_path / "out_t.xml"))
    monkeypatch.setattr(cli, "render", lambda *_args, **_kwargs: StepResult.ok(rendered))

    monkeypatch.setattr(
        cli,
        "score",
        lambda *_args, **_kwargs: StepResult.ok(tmp_path / "quality_report.json", metrics={"judgment": "REVIEW"}),
    )
    assert cli.main(["convert", "--input", str(input_path), "--output", str(output_path)]) == 1

    monkeypatch.setattr(
        cli,
        "score",
        lambda *_args, **_kwargs: StepResult.ok(tmp_path / "quality_report.json", metrics={"judgment": "FAIL"}),
    )
    assert cli.main(["convert", "--input", str(input_path), "--output", str(output_path)]) == 2


def test_main_convert_maps_input_errors_to_exit_code_3(monkeypatch, tmp_path: Path) -> None:
    from pipeline import __main__ as cli

    input_path = tmp_path / "missing.png"
    output_path = tmp_path / "song.mid"
    monkeypatch.setattr(cli, "load", lambda *_args, **_kwargs: (_ for _ in ()).throw(IngestError("bad input")))

    assert cli.main(["convert", "--input", str(input_path), "--output", str(output_path)]) == 3


def test_main_quality_runs_score_command(monkeypatch, tmp_path: Path) -> None:
    from pipeline import __main__ as cli

    musicxml_path = tmp_path / "score.xml"
    midi_path = tmp_path / "score.mid"
    musicxml_path.write_text("<score-partwise version=\"4.0\"><part-list/></score-partwise>", encoding="utf-8")
    midi_path.write_bytes(b"MThd")

    calls: list[tuple[Path, Path, Path]] = []

    def fake_score(musicxml: Path, midi: Path, output_dir: Path) -> StepResult:
        calls.append((musicxml, midi, output_dir))
        return StepResult.ok(output_dir / "quality_report.json", metrics={"judgment": "PASS"})

    monkeypatch.setattr(cli, "score", fake_score)

    exit_code = cli.main(["quality", "--musicxml", str(musicxml_path), "--midi", str(midi_path)])

    assert exit_code == 0
    assert calls == [(musicxml_path, midi_path, midi_path.parent)]


def test_main_convert_supports_multi_page_inputs(monkeypatch, tmp_path: Path) -> None:
    from pipeline import __main__ as cli

    input_path = tmp_path / "score.pdf"
    input_path.write_bytes(b"%PDF")
    output_path = tmp_path / "song.mid"

    source_pages = [tmp_path / "score_p001.png", tmp_path / "score_p002.png"]
    preprocessed_pages = [tmp_path / "pre_001.png", tmp_path / "pre_002.png"]
    musicxml_pages = [tmp_path / "page_001.xml", tmp_path / "page_002.xml"]
    transformed_pages = [tmp_path / "page_001_transformed.xml", tmp_path / "page_002_transformed.xml"]
    rendered_pages = [tmp_path / "page_001.mid", tmp_path / "page_002.mid"]

    for page in source_pages + preprocessed_pages:
        page.write_bytes(b"png")
    for page in musicxml_pages + transformed_pages:
        page.write_text("<score-partwise version=\"4.0\"><part-list/></score-partwise>", encoding="utf-8")

    _write_test_midi(rendered_pages[0], 60)
    _write_test_midi(rendered_pages[1], 64)

    processed_images: list[Path] = []
    transcribed_images: list[Path] = []

    monkeypatch.setattr(cli, "load", lambda *_args, **_kwargs: StepResult.ok(source_pages))

    def fake_preprocess(image_path: Path, *_args: object, **_kwargs: object) -> StepResult:
        processed_images.append(image_path)
        return StepResult.ok(preprocessed_pages[len(processed_images) - 1])

    monkeypatch.setattr(cli, "preprocess", fake_preprocess)
    monkeypatch.setattr(cli, "validate", lambda image_path, *_args, **_kwargs: StepResult.ok(image_path))

    def fake_transcribe(image_path: Path, *_args: object, **_kwargs: object) -> StepResult:
        transcribed_images.append(image_path)
        return StepResult.ok(musicxml_pages[len(transcribed_images) - 1])

    monkeypatch.setattr(cli, "transcribe", fake_transcribe)
    monkeypatch.setattr(
        cli,
        "transform",
        lambda musicxml_path, *_args, **_kwargs: StepResult.ok(
            transformed_pages[musicxml_pages.index(musicxml_path)]
        ),
    )
    monkeypatch.setattr(
        cli,
        "render",
        lambda transformed_path, *_args, **_kwargs: StepResult.ok(
            rendered_pages[transformed_pages.index(transformed_path)]
        ),
    )

    score_calls: list[tuple[Path, Path, Path]] = []

    def fake_score(musicxml_path: Path, midi_path: Path, output_dir: Path) -> StepResult:
        score_calls.append((musicxml_path, midi_path, output_dir))
        page_index = transformed_pages.index(musicxml_path)
        judgment = "PASS" if page_index == 0 else "REVIEW"
        return StepResult.ok(
            output_dir / "quality_report.json",
            metrics={
                "judgment": judgment,
                "overall_score": 0.91 if page_index == 0 else 0.67,
                "omr_confidence": 0.9,
                "measure_completeness": 0.8,
                "pitch_range_validity": 0.85,
                "part_detection_rate": 1.0,
                "total_measures": 8,
                "total_notes": 24,
            },
            warnings=[f"page_{page_index + 1}_warning"],
        )

    monkeypatch.setattr(cli, "score", fake_score)

    exit_code = cli.main(["convert", "--input", str(input_path), "--output", str(output_path)])

    assert exit_code == 1
    assert processed_images == source_pages
    assert transcribed_images == preprocessed_pages
    assert len(score_calls) == 2
    assert output_path.exists()

    merged_midi = MidiFile(output_path)
    assert merged_midi.type == 1
    assert len(merged_midi.tracks) == 4

    report = json.loads((output_path.parent / "quality_report.json").read_text(encoding="utf-8"))
    assert report["page_count"] == 2
    assert report["judgment"] == "REVIEW"
    assert len(report["pages"]) == 2


def test_main_convert_pages_option_filters_multi_page_inputs(monkeypatch, tmp_path: Path) -> None:
    from pipeline import __main__ as cli

    input_path = tmp_path / "score.pdf"
    input_path.write_bytes(b"%PDF")
    output_path = tmp_path / "song.mid"

    source_pages = [
        tmp_path / "score_p001.png",
        tmp_path / "score_p002.png",
        tmp_path / "score_p003.png",
    ]
    preprocessed_pages = [
        tmp_path / "pre_001.png",
        tmp_path / "pre_002.png",
        tmp_path / "pre_003.png",
    ]
    musicxml_pages = [
        tmp_path / "page_001.xml",
        tmp_path / "page_002.xml",
        tmp_path / "page_003.xml",
    ]
    transformed_pages = [
        tmp_path / "page_001_transformed.xml",
        tmp_path / "page_002_transformed.xml",
        tmp_path / "page_003_transformed.xml",
    ]
    rendered_pages = [
        tmp_path / "page_001.mid",
        tmp_path / "page_002.mid",
        tmp_path / "page_003.mid",
    ]

    for page in source_pages + preprocessed_pages:
        page.write_bytes(b"png")
    for page in musicxml_pages + transformed_pages:
        page.write_text("<score-partwise version=\"4.0\"><part-list/></score-partwise>", encoding="utf-8")

    _write_test_midi(rendered_pages[0], 60)
    _write_test_midi(rendered_pages[1], 64)
    _write_test_midi(rendered_pages[2], 67)

    processed_images: list[Path] = []
    transcribed_images: list[Path] = []

    monkeypatch.setattr(cli, "load", lambda *_args, **_kwargs: StepResult.ok(source_pages))

    def fake_preprocess(image_path: Path, *_args: object, **_kwargs: object) -> StepResult:
        processed_images.append(image_path)
        return StepResult.ok(preprocessed_pages[source_pages.index(image_path)])

    monkeypatch.setattr(cli, "preprocess", fake_preprocess)
    monkeypatch.setattr(cli, "validate", lambda image_path, *_args, **_kwargs: StepResult.ok(image_path))

    def fake_transcribe(image_path: Path, *_args: object, **_kwargs: object) -> StepResult:
        transcribed_images.append(image_path)
        return StepResult.ok(musicxml_pages[preprocessed_pages.index(image_path)])

    monkeypatch.setattr(cli, "transcribe", fake_transcribe)
    monkeypatch.setattr(
        cli,
        "transform",
        lambda musicxml_path, *_args, **_kwargs: StepResult.ok(
            transformed_pages[musicxml_pages.index(musicxml_path)]
        ),
    )
    monkeypatch.setattr(
        cli,
        "render",
        lambda transformed_path, *_args, **_kwargs: StepResult.ok(
            rendered_pages[transformed_pages.index(transformed_path)]
        ),
    )
    monkeypatch.setattr(
        cli,
        "score",
        lambda *_args, **_kwargs: StepResult.ok(
            tmp_path / "quality_report.json",
            metrics={
                "judgment": "PASS",
                "overall_score": 0.9,
                "omr_confidence": 0.9,
                "measure_completeness": 0.9,
                "pitch_range_validity": 0.9,
                "part_detection_rate": 1.0,
                "total_measures": 4,
                "total_notes": 16,
            },
        ),
    )

    exit_code = cli.main(
        [
            "convert",
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--pages",
            "2-3",
        ]
    )

    assert exit_code == 0
    assert processed_images == [source_pages[1], source_pages[2]]
    assert transcribed_images == [preprocessed_pages[1], preprocessed_pages[2]]


def test_main_convert_pages_option_rejects_out_of_range(monkeypatch, tmp_path: Path) -> None:
    from pipeline import __main__ as cli

    input_path = tmp_path / "score.pdf"
    input_path.write_bytes(b"%PDF")
    output_path = tmp_path / "song.mid"
    source_pages = [tmp_path / "score_p001.png", tmp_path / "score_p002.png"]
    for page in source_pages:
        page.write_bytes(b"png")

    monkeypatch.setattr(cli, "load", lambda *_args, **_kwargs: StepResult.ok(source_pages))

    exit_code = cli.main(
        [
            "convert",
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--pages",
            "9-11",
        ]
    )

    assert exit_code == 3


def test_main_convert_dry_run_stops_before_render_and_score(monkeypatch, tmp_path: Path) -> None:
    from pipeline import __main__ as cli
    from pipeline.cli_config import CliPipelineConfig, QualityThresholds

    input_path = tmp_path / "score.png"
    input_path.write_bytes(b"png")
    output_path = tmp_path / "song.mid"

    monkeypatch.setattr(
        cli,
        "load_pipeline_config",
        lambda *_args, **_kwargs: CliPipelineConfig(
            properties_path=Path("config/audiveris.properties"),
            quality=QualityThresholds(pass_threshold=0.8, warn_threshold=0.6),
        ),
    )
    monkeypatch.setattr(cli, "load", lambda *_args, **_kwargs: StepResult.ok([input_path]))
    monkeypatch.setattr(cli, "preprocess", lambda *_args, **_kwargs: StepResult.ok(tmp_path / "pre.png"))
    monkeypatch.setattr(cli, "validate", lambda image_path, *_args, **_kwargs: StepResult.ok(image_path))
    monkeypatch.setattr(
        cli,
        "transcribe",
        lambda *_args, **_kwargs: StepResult.ok(tmp_path / "score.xml"),
    )
    monkeypatch.setattr(
        cli,
        "transform",
        lambda *_args, **_kwargs: StepResult.ok(tmp_path / "score_transformed.xml"),
    )
    monkeypatch.setattr(
        cli,
        "render",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("render should not run during dry-run")),
    )
    monkeypatch.setattr(
        cli,
        "score",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("score should not run during dry-run")),
    )

    exit_code = cli.main(
        [
            "convert",
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--dry-run",
        ]
    )

    assert exit_code == 0
    assert not output_path.exists()


def test_main_convert_uses_custom_report_and_quality_threshold(monkeypatch, tmp_path: Path) -> None:
    from pipeline import __main__ as cli
    from pipeline.cli_config import CliPipelineConfig, QualityThresholds

    input_path = tmp_path / "score.png"
    input_path.write_bytes(b"png")
    output_path = tmp_path / "song.mid"
    rendered = tmp_path / "rendered.mid"
    rendered.write_bytes(b"MThd")
    generated_report = tmp_path / "quality_report.json"
    generated_report.write_text(
        json.dumps({"overall_score": 0.72, "judgment": "REVIEW", "output_midi": rendered.name}),
        encoding="utf-8",
    )
    custom_report = tmp_path / "reports" / "song.quality.json"

    monkeypatch.setattr(
        cli,
        "load_pipeline_config",
        lambda *_args, **_kwargs: CliPipelineConfig(
            properties_path=Path("config/audiveris.properties"),
            quality=QualityThresholds(pass_threshold=0.85, warn_threshold=0.65),
        ),
    )
    monkeypatch.setattr(cli, "load", lambda *_args, **_kwargs: StepResult.ok([input_path]))
    monkeypatch.setattr(cli, "preprocess", lambda *_args, **_kwargs: StepResult.ok(tmp_path / "pre.png"))
    monkeypatch.setattr(cli, "validate", lambda image_path, *_args, **_kwargs: StepResult.ok(image_path))
    monkeypatch.setattr(cli, "transcribe", lambda *_args, **_kwargs: StepResult.ok(tmp_path / "score.xml"))
    monkeypatch.setattr(cli, "transform", lambda *_args, **_kwargs: StepResult.ok(tmp_path / "score_transformed.xml"))
    monkeypatch.setattr(cli, "render", lambda *_args, **_kwargs: StepResult.ok(rendered))
    monkeypatch.setattr(
        cli,
        "score",
        lambda *_args, **_kwargs: StepResult.ok(
            generated_report,
            metrics={"judgment": "REVIEW", "overall_score": 0.72},
        ),
    )

    exit_code = cli.main(
        [
            "convert",
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--quality-threshold",
            "0.9",
            "--report",
            str(custom_report),
        ]
    )

    assert exit_code == 1
    payload = json.loads(custom_report.read_text(encoding="utf-8"))
    assert payload["judgment"] == "REVIEW"
    assert payload["output_midi"] == output_path.name


def test_main_convert_passes_properties_path_and_tuning_to_downstream_steps(monkeypatch, tmp_path: Path) -> None:
    from pipeline import __main__ as cli
    from pipeline.cli_config import CliPipelineConfig, MidiSettings, PreprocessSettings, QualityThresholds

    input_path = tmp_path / "score.png"
    input_path.write_bytes(b"png")
    output_path = tmp_path / "song.mid"
    custom_properties = tmp_path / "custom.properties"
    custom_tuning = [38, 45, 50, 55, 59, 64]

    calls: dict[str, object] = {}

    monkeypatch.setattr(
        cli,
        "load_pipeline_config",
        lambda *_args, **_kwargs: CliPipelineConfig(
            properties_path=custom_properties,
            preprocessing=PreprocessSettings(target_dpi=240, min_dpi=180.0, deskew_max_angle=3.0, clahe_clip_limit=1.5),
            quality=QualityThresholds(pass_threshold=0.8, warn_threshold=0.6),
            midi=MidiSettings(default_tempo=140, pitch_bend_range=4),
        ),
    )
    def fake_load(input_path: Path, cache_dir: Path, *, target_dpi: int = 300) -> StepResult:
        calls["target_dpi"] = target_dpi
        return StepResult.ok([input_path])

    monkeypatch.setattr(cli, "load", fake_load)

    def fake_preprocess(image_path: Path, output_dir: Path, *, deskew_max_angle: float = 10.0, clahe_clip_limit: float = 2.0) -> StepResult:
        calls["deskew_max_angle"] = deskew_max_angle
        calls["clahe_clip_limit"] = clahe_clip_limit
        return StepResult.ok(tmp_path / "pre.png")

    monkeypatch.setattr(cli, "preprocess", fake_preprocess)

    def fake_validate(image_path: Path, *, minimum_dpi: float = 200.0, recommended_dpi: float = 300.0) -> StepResult:
        calls["minimum_dpi"] = minimum_dpi
        calls["recommended_dpi"] = recommended_dpi
        return StepResult.ok(image_path)

    monkeypatch.setattr(cli, "validate", fake_validate)

    def fake_transcribe(image_path: Path, output_dir: Path, *, runner: object | None = None, properties_path: Path | None = None) -> StepResult:
        calls["properties_path"] = properties_path
        return StepResult.ok(tmp_path / "score.xml")

    monkeypatch.setattr(cli, "transcribe", fake_transcribe)
    monkeypatch.setattr(cli, "_load_tuning", lambda *_args, **_kwargs: custom_tuning)

    def fake_transform(musicxml_path: Path, output_dir: Path, *, tuning: list[int] | None = None, **_kwargs: object) -> StepResult:
        calls["tuning"] = tuning
        calls["preprocessed_image_path"] = _kwargs.get("preprocessed_image_path")
        return StepResult.ok(tmp_path / "score_transformed.xml")

    monkeypatch.setattr(cli, "transform", fake_transform)

    def fake_render(musicxml_path: Path, output_dir: Path, *, default_bpm: int = 120, pitch_bend_range: int = 2) -> StepResult:
        calls["default_bpm"] = default_bpm
        calls["pitch_bend_range"] = pitch_bend_range
        return StepResult.ok(tmp_path / "rendered.mid")

    monkeypatch.setattr(cli, "render", fake_render)
    monkeypatch.setattr(
        cli,
        "score",
        lambda *_args, **_kwargs: StepResult.ok(
            tmp_path / "quality_report.json",
            metrics={"judgment": "PASS", "overall_score": 0.95},
        ),
    )
    (tmp_path / "rendered.mid").write_bytes(b"MThd")
    (tmp_path / "quality_report.json").write_text(json.dumps({"overall_score": 0.95, "judgment": "PASS"}), encoding="utf-8")

    exit_code = cli.main(
        [
            "convert",
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--config",
            str(tmp_path / "pipeline.yaml"),
            "--tuning",
            "drop_d",
        ]
    )

    assert exit_code == 0
    assert calls["target_dpi"] == 240
    assert calls["properties_path"] == custom_properties
    assert calls["tuning"] == custom_tuning
    assert calls["preprocessed_image_path"] == tmp_path / "pre.png"
    assert calls["minimum_dpi"] == 180.0
    assert calls["recommended_dpi"] == 240.0
    assert calls["deskew_max_angle"] == 3.0
    assert calls["clahe_clip_limit"] == 1.5
    assert calls["default_bpm"] == 140
    assert calls["pitch_bend_range"] == 4


def test_main_convert_default_role_guitar_passed_to_transform(monkeypatch, tmp_path: Path) -> None:
    """--default-role guitar が transform() に default_role="guitar" として渡ることを確認する。"""
    from pipeline import __main__ as cli

    input_path = tmp_path / "score.png"
    input_path.write_bytes(b"png")
    output_path = tmp_path / "song.mid"
    rendered = tmp_path / "rendered.mid"
    rendered.write_bytes(b"MThd")

    transform_calls: list[dict[str, object]] = []

    def fake_transform(musicxml_path: object, output_dir: object, **kwargs: object) -> StepResult:
        transform_calls.append({"kwargs": kwargs})
        return StepResult.ok(tmp_path / "transformed.xml")

    monkeypatch.setattr(cli, "load", lambda *_a, **_k: StepResult.ok([input_path]))
    monkeypatch.setattr(cli, "preprocess", lambda *_a, **_k: StepResult.ok(tmp_path / "pre.png"))
    monkeypatch.setattr(cli, "validate", lambda image_path, *_a, **_k: StepResult.ok(image_path))
    monkeypatch.setattr(cli, "transcribe", lambda *_a, **_k: StepResult.ok(tmp_path / "score.xml"))
    monkeypatch.setattr(cli, "transform", fake_transform)
    monkeypatch.setattr(cli, "render", lambda *_a, **_k: StepResult.ok(rendered))
    monkeypatch.setattr(
        cli,
        "score",
        lambda *_a, **_k: StepResult.ok(
            tmp_path / "quality_report.json",
            metrics={"judgment": "PASS", "overall_score": 0.9},
        ),
    )

    exit_code = cli.main(
        [
            "convert",
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--default-role",
            "guitar",
        ]
    )

    assert exit_code == 0
    assert len(transform_calls) == 1
    assert transform_calls[0]["kwargs"].get("default_role") == "guitar"
