"""CLI configuration loading for pipeline entrypoints."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from pipeline.common import PipelineError


@dataclass(frozen=True)
class QualityThresholds:
    pass_threshold: float
    warn_threshold: float


@dataclass(frozen=True)
class PreprocessSettings:
    target_dpi: int = 300
    min_dpi: float = 200.0
    deskew_max_angle: float = 10.0
    clahe_clip_limit: float = 2.0


@dataclass(frozen=True)
class MidiSettings:
    default_tempo: int = 120
    pitch_bend_range: int = 2


@dataclass(frozen=True)
class CliPipelineConfig:
    properties_path: Path
    quality: QualityThresholds
    preprocessing: PreprocessSettings = PreprocessSettings()
    midi: MidiSettings = MidiSettings()


def load_pipeline_config(config_path: Path = Path("config/pipeline.yaml")) -> CliPipelineConfig:
    """Load CLI-facing pipeline configuration from YAML."""
    if not config_path.exists():
        raise PipelineError(f"Pipeline config not found: {config_path}")

    try:
        raw_content = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise PipelineError(f"Failed to read pipeline config: {config_path}") from exc

    if not isinstance(raw_content, dict):
        raise PipelineError(f"Pipeline config must be a mapping: {config_path}")

    audiveris = raw_content.get("audiveris", {})
    preprocessing = raw_content.get("preprocessing", {})
    quality = raw_content.get("quality", {})
    midi = raw_content.get("midi", {})
    if not isinstance(audiveris, dict) or not isinstance(preprocessing, dict) or not isinstance(quality, dict) or not isinstance(midi, dict):
        raise PipelineError(f"Pipeline config has invalid sections: {config_path}")

    properties_value = audiveris.get("properties_path", "config/audiveris.properties")
    if not isinstance(properties_value, str) or properties_value.strip() == "":
        raise PipelineError("audiveris.properties_path must be a non-empty string")

    pass_threshold = _as_threshold(quality.get("pass_threshold", 0.80), "quality.pass_threshold")
    warn_threshold = _as_threshold(quality.get("warn_threshold", 0.60), "quality.warn_threshold")
    if warn_threshold > pass_threshold:
        raise PipelineError("quality.warn_threshold must be <= quality.pass_threshold")

    return CliPipelineConfig(
        properties_path=_resolve_relative_path(config_path, properties_value),
        preprocessing=PreprocessSettings(
            target_dpi=_as_positive_int(
                preprocessing.get("target_dpi", 300),
                "preprocessing.target_dpi",
            ),
            min_dpi=_as_positive_float(
                preprocessing.get("min_dpi", 200.0),
                "preprocessing.min_dpi",
            ),
            deskew_max_angle=_as_positive_float(
                preprocessing.get("deskew_max_angle", 10.0),
                "preprocessing.deskew_max_angle",
            ),
            clahe_clip_limit=_as_positive_float(
                preprocessing.get("clahe_clip_limit", 2.0),
                "preprocessing.clahe_clip_limit",
            ),
        ),
        quality=QualityThresholds(pass_threshold=pass_threshold, warn_threshold=warn_threshold),
        midi=MidiSettings(
            default_tempo=_as_positive_int(midi.get("default_tempo", 120), "midi.default_tempo"),
            pitch_bend_range=_as_positive_int(midi.get("pitch_bend_range", 2), "midi.pitch_bend_range"),
        ),
    )


def _resolve_relative_path(config_path: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (config_path.parent / path).resolve()


def _as_threshold(value: object, field_name: str) -> float:
    if not isinstance(value, (int, float)):
        raise PipelineError(f"{field_name} must be numeric")
    threshold = float(value)
    if threshold < 0.0 or threshold > 1.0:
        raise PipelineError(f"{field_name} must be between 0.0 and 1.0")
    return threshold


def _as_positive_float(value: object, field_name: str) -> float:
    if not isinstance(value, (int, float)):
        raise PipelineError(f"{field_name} must be numeric")
    converted = float(value)
    if converted <= 0.0:
        raise PipelineError(f"{field_name} must be > 0")
    return converted


def _as_positive_int(value: object, field_name: str) -> int:
    if not isinstance(value, int):
        raise PipelineError(f"{field_name} must be an integer")
    if value <= 0:
        raise PipelineError(f"{field_name} must be > 0")
    return value