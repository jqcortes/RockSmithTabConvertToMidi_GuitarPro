"""Overall quality score judgment."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pipeline.quality.metrics import QualityMetrics

Judgment = Literal["PASS", "REVIEW", "FAIL"]


@dataclass(frozen=True)
class QualityDecision:
    """Overall quality score and categorical judgment."""

    overall_score: float
    judgment: Judgment


class QualityJudge:
    """Evaluate weighted quality score thresholds."""

    @staticmethod
    def evaluate(metrics: QualityMetrics) -> QualityDecision:
        """Calculate weighted score and return PASS / REVIEW / FAIL."""
        score = round(
            (0.40 * metrics.omr_confidence)
            + (0.30 * metrics.measure_completeness)
            + (0.15 * metrics.pitch_range_validity)
            + (0.15 * metrics.part_detection_rate),
            3,
        )
        if score >= 0.80:
            judgment: Judgment = "PASS"
        elif score >= 0.60:
            judgment = "REVIEW"
        else:
            judgment = "FAIL"
        return QualityDecision(overall_score=score, judgment=judgment)