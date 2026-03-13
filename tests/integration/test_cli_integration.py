"""Integration tests for CLI command wiring."""

from __future__ import annotations

import json
from pathlib import Path

from mido import MidiFile

from pipeline.common import StepResult


FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "musicxml"


def test_convert_command_runs_real_transform_render_and_quality(
    monkeypatch,
    tmp_path: Path,
) -> None:
    from pipeline import __main__ as cli

    input_path = tmp_path / "score.png"
    input_path.write_bytes(b"png")
    output_path = tmp_path / "song.mid"
    fixture_musicxml = FIXTURES_DIR / "quality_good.xml"

    monkeypatch.setattr(cli, "load", lambda *_args, **_kwargs: StepResult.ok([input_path]))
    monkeypatch.setattr(cli, "preprocess", lambda *_args, **_kwargs: StepResult.ok(input_path))
    monkeypatch.setattr(cli, "validate", lambda *_args, **_kwargs: StepResult.ok(input_path))
    monkeypatch.setattr(cli, "transcribe", lambda *_args, **_kwargs: StepResult.ok(fixture_musicxml))

    exit_code = cli.main(
        [
            "convert",
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--cache-dir",
            str(tmp_path / "cache"),
        ]
    )

    assert exit_code == 0
    assert output_path.exists()
    assert (output_path.parent / "quality_report.json").exists()

    midi_file = MidiFile(output_path)
    assert midi_file.type == 1
    assert len(midi_file.tracks) >= 2


def test_quality_command_runs_real_quality_score(tmp_path: Path) -> None:
    from pipeline import __main__ as cli
    from pipeline.render import render
    from pipeline.transform import transform

    fixture_musicxml = FIXTURES_DIR / "quality_good.xml"
    transformed_dir = tmp_path / "transform"
    render_dir = tmp_path / "render"
    quality_dir = tmp_path / "quality"

    transformed_result = transform(fixture_musicxml, transformed_dir)
    transformed_path = transformed_result.output_path
    assert isinstance(transformed_path, Path)

    rendered_result = render(transformed_path, render_dir)
    midi_path = rendered_result.output_path
    assert isinstance(midi_path, Path)

    exit_code = cli.main(
        [
            "quality",
            "--musicxml",
            str(transformed_path),
            "--midi",
            str(midi_path),
            "--output-dir",
            str(quality_dir),
        ]
    )

    assert exit_code == 0
    assert (quality_dir / "quality_report.json").exists()


def test_convert_command_supports_multi_page_pdf_flow(monkeypatch, tmp_path: Path) -> None:
    from pipeline import __main__ as cli

    input_path = tmp_path / "score.pdf"
    input_path.write_bytes(b"%PDF")
    output_path = tmp_path / "multi.mid"
    fixture_musicxml = FIXTURES_DIR / "quality_good.xml"

    page_one = tmp_path / "score_p001.png"
    page_two = tmp_path / "score_p002.png"
    page_one.write_bytes(b"png")
    page_two.write_bytes(b"png")

    monkeypatch.setattr(cli, "load", lambda *_args, **_kwargs: StepResult.ok([page_one, page_two]))
    monkeypatch.setattr(cli, "preprocess", lambda image_path, *_args, **_kwargs: StepResult.ok(image_path))
    monkeypatch.setattr(cli, "validate", lambda image_path, *_args, **_kwargs: StepResult.ok(image_path))
    monkeypatch.setattr(cli, "transcribe", lambda *_args, **_kwargs: StepResult.ok(fixture_musicxml))

    exit_code = cli.main(
        [
            "convert",
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--cache-dir",
            str(tmp_path / "cache"),
        ]
    )

    assert exit_code == 0
    assert output_path.exists()

    midi_file = MidiFile(output_path)
    assert midi_file.type == 1
    assert len(midi_file.tracks) >= 3

    report = json.loads((output_path.parent / "quality_report.json").read_text(encoding="utf-8"))
    assert report["page_count"] == 2
    assert report["judgment"] == "PASS"