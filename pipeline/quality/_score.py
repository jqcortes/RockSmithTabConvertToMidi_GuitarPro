"""score() - Quality ドメインの公開エントリポイント。"""

from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter

from pipeline.common import MetricValue, StepResult, get_logger
from pipeline.quality.errors import QualityError, QualityExecutionError
from pipeline.quality.judge import QualityJudge
from pipeline.quality.metrics import QualityMetricsCalculator
from pipeline.quality.reporter import QualityReporter
from pipeline.quality.validator import QualityInputValidator


def score(musicxml_path: Path, midi_path: Path, output_dir: Path) -> StepResult:
    """Calculate quality metrics and write the cached quality report."""
    logger = get_logger(__name__)
    report_path = output_dir / "quality_report.json"

    logger.info(
        "quality_score_start",
        musicxml_path=str(musicxml_path),
        midi_path=str(midi_path),
        output_dir=str(output_dir),
    )

    if report_path.exists():
        logger.info("quality_score_cache_hit", output_path=str(report_path))
        return _cached_result(report_path)

    started_at = perf_counter()
    try:
        validated = QualityInputValidator.validate(musicxml_path, midi_path)
        metrics_result = QualityMetricsCalculator.calculate(validated.tree)
        decision = QualityJudge.evaluate(metrics_result)
        processing_time_seconds = round(perf_counter() - started_at, 3)
        output_path = QualityReporter.write_report(
            musicxml_path=validated.musicxml_path,
            midi_path=validated.midi_path,
            output_dir=output_dir,
            metrics=metrics_result,
            decision=decision,
            processing_time_seconds=processing_time_seconds,
        )

        metrics: dict[str, MetricValue] = {
            "cached": False,
            "elapsed_seconds": processing_time_seconds,
            "overall_score": decision.overall_score,
            "judgment": decision.judgment,
            "omr_confidence": metrics_result.omr_confidence,
            "measure_completeness": metrics_result.measure_completeness,
            "pitch_range_validity": metrics_result.pitch_range_validity,
            "part_detection_rate": metrics_result.part_detection_rate,
            "total_measures": metrics_result.total_measures,
            "total_notes": metrics_result.total_notes,
        }
        warnings = [
            f"{warning['type']}: {warning['location']} ({warning['detail']})"
            for warning in metrics_result.warnings
        ]

        logger.info(
            "quality_score_complete",
            output_path=str(output_path),
            overall_score=decision.overall_score,
            judgment=decision.judgment,
        )
        return StepResult.ok(output_path=output_path, metrics=metrics, warnings=warnings)
    except QualityError:
        logger.exception("quality_score_failed", musicxml_path=str(musicxml_path), midi_path=str(midi_path))
        raise
    except Exception as exc:
        logger.exception(
            "quality_score_unexpected_error",
            musicxml_path=str(musicxml_path),
            midi_path=str(midi_path),
        )
        raise QualityExecutionError(str(exc)) from exc


def _cached_result(report_path: Path) -> StepResult:
    payload = _load_report_payload(report_path)
    metrics_payload = payload.get("metrics")
    stats_payload = payload.get("stats")

    metrics: dict[str, MetricValue] = {
        "cached": True,
        "elapsed_seconds": _dict_float(stats_payload, "processing_time_seconds"),
    }

    overall_score = payload.get("overall_score")
    if isinstance(overall_score, (int, float)):
        metrics["overall_score"] = float(overall_score)

    judgment = payload.get("judgment")
    if isinstance(judgment, str):
        metrics["judgment"] = judgment

    for key in (
        "omr_confidence",
        "measure_completeness",
        "pitch_range_validity",
        "part_detection_rate",
    ):
        value = _dict_float(metrics_payload, key)
        if value != 0.0 or _dict_has_key(metrics_payload, key):
            metrics[key] = value

    for key in ("total_measures", "total_notes"):
        value = _dict_int(stats_payload, key)
        if value != 0 or _dict_has_key(stats_payload, key):
            metrics[key] = value

    return StepResult.ok(
        output_path=report_path,
        metrics=metrics,
        warnings=_deserialize_warnings(payload.get("warnings")),
    )


def _load_report_payload(report_path: Path) -> dict[str, object]:
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if isinstance(payload, dict):
        return payload
    return {}


def _deserialize_warnings(raw_warnings: object) -> list[str]:
    if not isinstance(raw_warnings, list):
        return []

    warnings: list[str] = []
    for warning in raw_warnings:
        if isinstance(warning, str):
            warnings.append(warning)
            continue
        if isinstance(warning, dict):
            warning_type = str(warning.get("type", "warning"))
            location = str(warning.get("location", "unknown"))
            detail = str(warning.get("detail", ""))
            warnings.append(f"{warning_type}: {location} ({detail})")
    return warnings


def _dict_float(payload: object, key: str) -> float:
    if isinstance(payload, dict):
        value = payload.get(key)
        if isinstance(value, (int, float)):
            return float(value)
    return 0.0


def _dict_int(payload: object, key: str) -> int:
    if isinstance(payload, dict):
        value = payload.get(key)
        if isinstance(value, int):
            return value
    return 0


def _dict_has_key(payload: object, key: str) -> bool:
    return isinstance(payload, dict) and key in payload