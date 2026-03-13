"""JSON report generation for Quality scoring."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from pipeline.quality.judge import QualityDecision
from pipeline.quality.metrics import QualityMetrics


class QualityReporter:
    """Write quality scoring results to quality_report.json."""

    @staticmethod
    def write_report(
        *,
        musicxml_path: Path,
        midi_path: Path,
        output_dir: Path,
        metrics: QualityMetrics,
        decision: QualityDecision,
        processing_time_seconds: float,
    ) -> Path:
        """Serialize the quality report payload to JSON and return its path."""
        output_dir.mkdir(parents=True, exist_ok=True)
        report_path = output_dir / "quality_report.json"
        payload = {
            "input_file": musicxml_path.name,
            "output_midi": midi_path.name,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "overall_score": decision.overall_score,
            "judgment": decision.judgment,
            "metrics": {
                "omr_confidence": metrics.omr_confidence,
                "measure_completeness": metrics.measure_completeness,
                "pitch_range_validity": metrics.pitch_range_validity,
                "part_detection_rate": metrics.part_detection_rate,
            },
            "warnings": metrics.warnings,
            "stats": {
                "total_measures": metrics.total_measures,
                "total_notes": metrics.total_notes,
                "processing_time_seconds": processing_time_seconds,
            },
        }
        report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return report_path