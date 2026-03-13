"""tests for Quality JSON report generation."""

from __future__ import annotations

import json
from pathlib import Path


class TestQualityReporter:
    def test_write_report_serializes_quality_payload(self, tmp_path: Path) -> None:
        from pipeline.quality.judge import QualityDecision
        from pipeline.quality.metrics import QualityMetrics
        from pipeline.quality.reporter import QualityReporter

        metrics = QualityMetrics(
            omr_confidence=0.85,
            measure_completeness=1.0,
            pitch_range_validity=1.0,
            part_detection_rate=1.0,
            warnings=[],
            total_measures=3,
            total_notes=3,
        )
        decision = QualityDecision(overall_score=0.94, judgment="PASS")

        report_path = QualityReporter.write_report(
            musicxml_path=Path("input.xml"),
            midi_path=Path("output.mid"),
            output_dir=tmp_path,
            metrics=metrics,
            decision=decision,
            processing_time_seconds=1.25,
        )

        payload = json.loads(report_path.read_text(encoding="utf-8"))

        assert report_path.name == "quality_report.json"
        assert payload["input_file"] == "input.xml"
        assert payload["output_midi"] == "output.mid"
        assert payload["overall_score"] == 0.94
        assert payload["judgment"] == "PASS"
        assert payload["metrics"]["omr_confidence"] == 0.85
        assert payload["stats"]["total_measures"] == 3
        assert payload["stats"]["total_notes"] == 3
        assert payload["stats"]["processing_time_seconds"] == 1.25
        assert "timestamp" in payload