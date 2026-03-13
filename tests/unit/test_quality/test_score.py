"""tests for Quality scoring entrypoint."""

from __future__ import annotations

from pathlib import Path

import pytest
from mido import MidiFile


FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "musicxml"


class TestQualityScoreEntrypoint:
    def test_score_returns_cached_step_result_when_report_exists(self, tmp_path: Path) -> None:
        from pipeline.quality import score

        midi_path = tmp_path / "valid.mid"
        MidiFile(type=1).save(midi_path)
        report_path = tmp_path / "quality_report.json"
        report_path.write_text("{}", encoding="utf-8")

        result = score(FIXTURES_DIR / "quality_good.xml", midi_path, tmp_path)

        assert result.success is True
        assert result.output_path == report_path
        assert result.metrics["cached"] is True

    def test_score_restores_metrics_and_warnings_from_cached_report(self, tmp_path: Path) -> None:
        from pipeline.quality import score

        midi_path = tmp_path / "valid.mid"
        MidiFile(type=1).save(midi_path)
        report_path = tmp_path / "quality_report.json"
        report_path.write_text(
            "{\n"
            '  "overall_score": 0.67,\n'
            '  "judgment": "REVIEW",\n'
            '  "metrics": {\n'
            '    "omr_confidence": 0.7,\n'
            '    "measure_completeness": 0.8,\n'
            '    "pitch_range_validity": 0.9,\n'
            '    "part_detection_rate": 1.0\n'
            "  },\n"
            '  "warnings": [\n'
            '    {"type": "low_confidence", "location": "measure 4", "detail": "note omitted"}\n'
            "  ],\n"
            '  "stats": {\n'
            '    "total_measures": 12,\n'
            '    "total_notes": 42,\n'
            '    "processing_time_seconds": 1.234\n'
            "  }\n"
            "}",
            encoding="utf-8",
        )

        result = score(FIXTURES_DIR / "quality_good.xml", midi_path, tmp_path)

        assert result.success is True
        assert result.output_path == report_path
        assert result.metrics["cached"] is True
        assert result.metrics["overall_score"] == 0.67
        assert result.metrics["judgment"] == "REVIEW"
        assert result.metrics["omr_confidence"] == 0.7
        assert result.metrics["measure_completeness"] == 0.8
        assert result.metrics["pitch_range_validity"] == 0.9
        assert result.metrics["part_detection_rate"] == 1.0
        assert result.metrics["total_measures"] == 12
        assert result.metrics["total_notes"] == 42
        assert result.metrics["elapsed_seconds"] == 1.234
        assert result.warnings == ["low_confidence: measure 4 (note omitted)"]

    def test_score_writes_report_and_aggregates_metrics(self, tmp_path: Path) -> None:
        from pipeline.quality import score

        midi_path = tmp_path / "valid.mid"
        MidiFile(type=1).save(midi_path)

        result = score(FIXTURES_DIR / "quality_good.xml", midi_path, tmp_path)

        assert result.success is True
        assert result.output_path == tmp_path / "quality_report.json"
        assert result.metrics["cached"] is False
        assert result.metrics["overall_score"] == 0.94
        assert result.metrics["judgment"] == "PASS"
        assert result.metrics["measure_completeness"] == 1.0
        assert result.metrics["part_detection_rate"] == 1.0
        assert result.warnings == []

    def test_score_re_raises_validation_errors(self, tmp_path: Path) -> None:
        from pipeline.quality import score
        from pipeline.quality.errors import QualityValidationError

        with pytest.raises(QualityValidationError):
            score(tmp_path / "missing.xml", tmp_path / "missing.mid", tmp_path)

    def test_score_wraps_unexpected_errors(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        from pipeline.quality import score
        from pipeline.quality.errors import QualityExecutionError

        midi_path = tmp_path / "valid.mid"
        MidiFile(type=1).save(midi_path)

        def raise_runtime_error(*_args: object, **_kwargs: object) -> object:
            raise RuntimeError("boom")

        monkeypatch.setattr("pipeline.quality._score.QualityReporter.write_report", raise_runtime_error)

        with pytest.raises(QualityExecutionError, match="boom"):
            score(FIXTURES_DIR / "quality_good.xml", midi_path, tmp_path)