"""tests for Quality overall score judgment."""

from __future__ import annotations


class TestQualityJudge:
    def test_evaluate_returns_pass_for_high_score(self) -> None:
        from pipeline.quality.judge import QualityJudge
        from pipeline.quality.metrics import QualityMetrics

        metrics = QualityMetrics(
            omr_confidence=0.9,
            measure_completeness=0.9,
            pitch_range_validity=1.0,
            part_detection_rate=1.0,
            warnings=[],
            total_measures=3,
            total_notes=3,
        )

        result = QualityJudge.evaluate(metrics)

        assert result.overall_score == 0.93
        assert result.judgment == "PASS"

    def test_evaluate_returns_review_for_mid_score(self) -> None:
        from pipeline.quality.judge import QualityJudge
        from pipeline.quality.metrics import QualityMetrics

        metrics = QualityMetrics(
            omr_confidence=0.6,
            measure_completeness=0.7,
            pitch_range_validity=0.8,
            part_detection_rate=0.6,
            warnings=[],
            total_measures=1,
            total_notes=1,
        )

        result = QualityJudge.evaluate(metrics)

        assert result.overall_score == 0.66
        assert result.judgment == "REVIEW"

    def test_evaluate_returns_fail_for_low_score(self) -> None:
        from pipeline.quality.judge import QualityJudge
        from pipeline.quality.metrics import QualityMetrics

        metrics = QualityMetrics(
            omr_confidence=0.2,
            measure_completeness=0.4,
            pitch_range_validity=0.5,
            part_detection_rate=0.5,
            warnings=[],
            total_measures=1,
            total_notes=1,
        )

        result = QualityJudge.evaluate(metrics)

        assert result.overall_score == 0.35
        assert result.judgment == "FAIL"
