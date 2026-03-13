"""tests for Quality metrics calculation."""

from __future__ import annotations

from pathlib import Path

from lxml import etree


FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "musicxml"


class TestQualityMetricsCalculator:
    def test_calculate_returns_expected_metrics_for_good_fixture(self) -> None:
        from pipeline.quality.metrics import QualityMetricsCalculator

        tree = etree.parse(str(FIXTURES_DIR / "quality_good.xml"))

        result = QualityMetricsCalculator.calculate(tree)

        assert result.omr_confidence == 0.85
        assert result.measure_completeness == 1.0
        assert result.pitch_range_validity == 1.0
        assert result.part_detection_rate == 1.0
        assert result.total_measures == 3
        assert result.total_notes == 3
        assert result.warnings == []

    def test_calculate_records_measure_incomplete_warning(self) -> None:
        from pipeline.quality.metrics import QualityMetricsCalculator

        tree = etree.parse(str(FIXTURES_DIR / "quality_measure_incomplete.xml"))

        result = QualityMetricsCalculator.calculate(tree)

        assert result.measure_completeness == 0.0
        assert any(warning["type"] == "MEASURE_INCOMPLETE" for warning in result.warnings)

    def test_calculate_records_out_of_range_warning_and_excludes_drums(self) -> None:
        from pipeline.quality.metrics import QualityMetricsCalculator

        tree = etree.parse(str(FIXTURES_DIR / "quality_out_of_range.xml"))

        result = QualityMetricsCalculator.calculate(tree)

        assert result.pitch_range_validity == 0.5
        assert any(warning["type"] == "PITCH_OUT_OF_RANGE" for warning in result.warnings)

    def test_calculate_falls_back_for_missing_confidence_and_partial_part_detection(self) -> None:
        from pipeline.quality.metrics import QualityMetricsCalculator

        tree = etree.parse(str(FIXTURES_DIR / "render_techniques.xml"))

        result = QualityMetricsCalculator.calculate(tree, expected_parts=["guitar", "bass"])

        assert 0.0 <= result.omr_confidence <= 1.0
        assert result.part_detection_rate == 0.5
