"""CLI entrypoint for the band-score-to-midi pipeline."""

from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from mido import MetaMessage, MidiFile, MidiTrack

from pipeline.cli_config import CliPipelineConfig, MidiSettings, PreprocessSettings, QualityThresholds, load_pipeline_config
from pipeline.common import IngestError, PipelineError, get_logger
from pipeline.ingest.image_loader import load
from pipeline.ingest.preprocessor import preprocess
from pipeline.ingest.validator import validate
from pipeline.omr import transcribe
from pipeline.omr.errors import OmrError
from pipeline.quality import score
from pipeline.render import render
from pipeline.transform import transform
from pipeline.transform.guitar_fixer import GuitarFixer

_LOG = get_logger(__name__)


@dataclass(frozen=True)
class _ConvertedPage:
    page_number: int
    source_image: Path
    transformed_path: Path
    midi_path: Path
    quality_result: object


def main(argv: Sequence[str] | None = None) -> int:
    """Parse CLI arguments and dispatch to subcommands."""
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        if args.command == "convert":
            return _run_convert(
                args.input,
                args.output,
                args.cache_dir,
                args.config,
                args.tuning,
                args.quality_threshold,
                args.report,
                args.dry_run,
            )
        if args.command == "quality":
            return _run_quality(args.musicxml, args.midi, args.output_dir)
        parser.print_help()
        return 3
    except OmrError as exc:
        _LOG.exception("cli_omr_failure", error=str(exc))
        return 4
    except IngestError as exc:
        _LOG.exception("cli_input_failure", error=str(exc))
        return 3
    except PipelineError as exc:
        _LOG.exception("cli_pipeline_failure", error=str(exc))
        return 3


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="band-score-to-midi")
    subparsers = parser.add_subparsers(dest="command")

    convert_parser = subparsers.add_parser("convert")
    convert_parser.add_argument("--input", type=Path, required=True)
    convert_parser.add_argument("--output", type=Path, required=True)
    convert_parser.add_argument("--config", type=Path, default=Path("config/pipeline.yaml"))
    convert_parser.add_argument("--tuning", type=str, default="standard")
    convert_parser.add_argument("--quality-threshold", type=float, default=None)
    convert_parser.add_argument("--cache-dir", type=Path, default=Path(".cache"))
    convert_parser.add_argument("--report", type=Path, default=None)
    convert_parser.add_argument("--dry-run", action="store_true")

    quality_parser = subparsers.add_parser("quality")
    quality_parser.add_argument("--musicxml", type=Path, required=True)
    quality_parser.add_argument("--midi", type=Path, required=True)
    quality_parser.add_argument("--output-dir", type=Path, default=None)
    return parser


def _run_convert(
    input_path: Path,
    output_path: Path,
    cache_dir: Path,
    config_path: Path,
    tuning_name: str,
    quality_threshold: float | None,
    report_path: Path | None,
    dry_run: bool,
) -> int:
    cli_config = load_pipeline_config(config_path)
    tuning = _load_tuning(tuning_name)
    thresholds = _resolve_quality_thresholds(cli_config, quality_threshold)
    actual_report_path = report_path if report_path is not None else output_path.parent / "quality_report.json"

    ingest_result = load(
        input_path,
        cache_dir=cache_dir / "ingest",
        target_dpi=cli_config.preprocessing.target_dpi,
    )
    source_images = _path_list(ingest_result.output_path)

    if len(source_images) == 1:
        return _run_single_page_convert(
            source_images[0],
            output_path,
            cache_dir,
            cli_config.properties_path,
            tuning,
            cli_config.preprocessing,
            cli_config.midi,
            thresholds,
            actual_report_path,
            dry_run,
        )

    prepared_pages = []
    for index, source_image in enumerate(source_images, start=1):
        try:
            prepared_pages.append(
                _prepare_page(
                    source_image,
                    page_number=index,
                    cache_dir=cache_dir,
                    properties_path=cli_config.properties_path,
                    tuning=tuning,
                    preprocessing=cli_config.preprocessing,
                )
            )
        except PipelineError as exc:
            _LOG.warning(
                "cli_page_skipped",
                page=index,
                source=str(source_image),
                reason=str(exc),
            )

    if not prepared_pages:
        _LOG.error("cli_all_pages_failed", total=len(source_images))
        return 3

    if dry_run:
        _LOG.info("cli_convert_dry_run_complete", page_count=len(prepared_pages))
        return 0

    converted_pages = [
        _render_and_score_page(prepared_page, cache_dir=cache_dir, midi_settings=cli_config.midi)
        for prepared_page in prepared_pages
    ]
    _concatenate_midis([page.midi_path for page in converted_pages], output_path)
    aggregate_report = _write_multi_page_quality_report(
        input_path,
        output_path,
        converted_pages,
        actual_report_path,
        thresholds,
    )
    return _exit_code_from_judgment(str(aggregate_report["judgment"]))


def _run_single_page_convert(
    source_image: Path,
    output_path: Path,
    cache_dir: Path,
    properties_path: Path,
    tuning: list[int],
    preprocessing: PreprocessSettings,
    midi_settings: MidiSettings,
    thresholds: QualityThresholds,
    report_path: Path,
    dry_run: bool,
) -> int:
    prepared_page = _prepare_page(
        source_image,
        page_number=1,
        cache_dir=cache_dir,
        properties_path=properties_path,
        tuning=tuning,
        preprocessing=preprocessing,
    )

    if dry_run:
        _LOG.info("cli_convert_dry_run_complete", page_count=1)
        return 0

    render_result = render(
        prepared_page.transformed_path,
        cache_dir / "render",
        default_bpm=midi_settings.default_tempo,
        pitch_bend_range=midi_settings.pitch_bend_range,
    )
    rendered_path = _as_path(render_result.output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if rendered_path != output_path:
        shutil.copy2(rendered_path, output_path)

    quality_result = score(prepared_page.transformed_path, output_path, output_path.parent)
    judgment = _resolve_quality_result_judgment(quality_result, thresholds)
    _finalize_single_page_report(
        generated_report_path=_as_path(quality_result.output_path),
        output_path=output_path,
        report_path=report_path,
        judgment=judgment,
    )
    return _exit_code_from_judgment(judgment)


@dataclass(frozen=True)
class _PreparedPage:
    page_number: int
    source_image: Path
    transformed_path: Path


def _prepare_page(
    source_image: Path,
    *,
    page_number: int,
    cache_dir: Path,
    properties_path: Path,
    tuning: list[int],
    preprocessing: PreprocessSettings,
) -> _PreparedPage:
    page_dir = cache_dir / f"page_{page_number:03d}"

    preprocess_result = preprocess(
        source_image,
        output_dir=page_dir / "preprocess",
        deskew_max_angle=preprocessing.deskew_max_angle,
        clahe_clip_limit=preprocessing.clahe_clip_limit,
    )
    preprocessed_image = _as_path(preprocess_result.output_path)
    validate(
        preprocessed_image,
        minimum_dpi=preprocessing.min_dpi,
        recommended_dpi=float(preprocessing.target_dpi),
    )

    omr_result = transcribe(preprocessed_image, page_dir / "omr", properties_path=properties_path)
    musicxml_path = _as_path(omr_result.output_path)

    transform_result = transform(musicxml_path, page_dir / "transform", tuning=tuning)
    transformed_path = _as_path(transform_result.output_path)

    return _PreparedPage(
        page_number=page_number,
        source_image=source_image,
        transformed_path=transformed_path,
    )


def _render_and_score_page(
    prepared_page: _PreparedPage,
    *,
    cache_dir: Path,
    midi_settings: MidiSettings,
) -> _ConvertedPage:
    page_dir = cache_dir / f"page_{prepared_page.page_number:03d}"

    render_result = render(
        prepared_page.transformed_path,
        page_dir / "render",
        default_bpm=midi_settings.default_tempo,
        pitch_bend_range=midi_settings.pitch_bend_range,
    )
    rendered_path = _as_path(render_result.output_path)

    quality_result = score(prepared_page.transformed_path, rendered_path, page_dir / "quality")
    return _ConvertedPage(
        page_number=prepared_page.page_number,
        source_image=prepared_page.source_image,
        transformed_path=prepared_page.transformed_path,
        midi_path=rendered_path,
        quality_result=quality_result,
    )


def _run_quality(musicxml_path: Path, midi_path: Path, output_dir: Path | None) -> int:
    actual_output_dir = output_dir if output_dir is not None else midi_path.parent
    quality_result = score(musicxml_path, midi_path, actual_output_dir)
    judgment = str(quality_result.metrics.get("judgment", "PASS"))
    return _exit_code_from_judgment(judgment)


def _path_list(output_path: object) -> list[Path]:
    if isinstance(output_path, list):
        if len(output_path) == 0:
            raise IngestError("Ingest step produced no page outputs")
        normalized_paths: list[Path] = []
        for value in output_path:
            if not isinstance(value, Path):
                raise IngestError("Unexpected ingest output path entry type")
            normalized_paths.append(value)
        return normalized_paths
    if isinstance(output_path, Path):
        return [output_path]
    raise IngestError("Unexpected ingest output path type")


def _as_path(output_path: object) -> Path:
    if isinstance(output_path, Path):
        return output_path
    raise IngestError("Unexpected step output path type")


def _concatenate_midis(midi_paths: Sequence[Path], output_path: Path) -> None:
    if len(midi_paths) == 0:
        raise IngestError("No rendered MIDI files were produced")
    if len(midi_paths) == 1:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(midi_paths[0], output_path)
        return

    midi_files = [MidiFile(path) for path in midi_paths]
    ticks_per_beat = midi_files[0].ticks_per_beat
    if any(midi_file.ticks_per_beat != ticks_per_beat for midi_file in midi_files[1:]):
        raise PipelineError("Cannot concatenate MIDI files with different ticks_per_beat values")

    combined = MidiFile(type=1, ticks_per_beat=ticks_per_beat)
    cumulative_ticks = 0

    for midi_file in midi_files:
        page_duration = max((_track_duration(track) for track in midi_file.tracks), default=0)
        for track in midi_file.tracks:
            new_track = MidiTrack()
            _append_track_with_offset(new_track, track, cumulative_ticks)
            new_track.append(MetaMessage("end_of_track", time=0))
            combined.tracks.append(new_track)
        cumulative_ticks += page_duration

    output_path.parent.mkdir(parents=True, exist_ok=True)
    combined.save(str(output_path))


def _append_track_with_offset(target: MidiTrack, source: MidiTrack, offset_ticks: int) -> None:
    first_message = True
    for message in source:
        if message.type == "end_of_track":
            continue
        delta_time = int(message.time)
        if first_message:
            delta_time += offset_ticks
            first_message = False
        target.append(message.copy(time=delta_time))


def _track_duration(track: MidiTrack) -> int:
    return sum(int(message.time) for message in track)


def _write_multi_page_quality_report(
    input_path: Path,
    output_path: Path,
    converted_pages: Sequence[_ConvertedPage],
    report_path: Path,
    thresholds: QualityThresholds,
) -> dict[str, object]:
    page_payloads = [_page_report_payload(page) for page in converted_pages]
    page_count = len(converted_pages)
    metric_names = [
        "omr_confidence",
        "measure_completeness",
        "pitch_range_validity",
        "part_detection_rate",
    ]
    overall_scores = [_metric_float(_result_metrics(page.quality_result), "overall_score") for page in converted_pages]
    judgments = [_judgment_from_score(score, thresholds) for score in overall_scores]
    warnings = [warning for page in converted_pages for warning in _warnings_from_result(page.quality_result)]
    total_measures = sum(_metric_int(_result_metrics(page.quality_result), "total_measures") for page in converted_pages)
    total_notes = sum(_metric_int(_result_metrics(page.quality_result), "total_notes") for page in converted_pages)
    processing_time_seconds = round(
        sum(_metric_float(_result_metrics(page.quality_result), "elapsed_seconds") for page in converted_pages),
        3,
    )
    payload = {
        "input_file": input_path.name,
        "output_midi": output_path.name,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "page_count": page_count,
        "overall_score": round(min(overall_scores, default=0.0), 3),
        "judgment": _worst_judgment(judgments),
        "metrics": {
            metric_name: round(
                sum(_metric_float(_result_metrics(page.quality_result), metric_name) for page in converted_pages) / page_count,
                3,
            )
            for metric_name in metric_names
        },
        "warnings": warnings,
        "stats": {
            "total_measures": total_measures,
            "total_notes": total_notes,
            "processing_time_seconds": processing_time_seconds,
        },
        "pages": page_payloads,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload


def _finalize_single_page_report(
    *,
    generated_report_path: Path,
    output_path: Path,
    report_path: Path,
    judgment: str,
) -> None:
    payload = _load_json_payload(generated_report_path)
    payload["judgment"] = judgment
    payload["output_midi"] = output_path.name
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _load_json_payload(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if isinstance(payload, dict):
        return payload
    return {}


def _page_report_payload(page: _ConvertedPage) -> dict[str, object]:
    quality_result = page.quality_result
    metrics = _result_metrics(quality_result)
    warnings = _warnings_from_result(quality_result)
    return {
        "page_number": page.page_number,
        "source_image": page.source_image.name,
        "input_file": page.transformed_path.name,
        "output_midi": page.midi_path.name,
        "overall_score": _metric_float(metrics, "overall_score"),
        "judgment": _judgment_from_result(quality_result),
        "metrics": {
            "omr_confidence": _metric_float(metrics, "omr_confidence"),
            "measure_completeness": _metric_float(metrics, "measure_completeness"),
            "pitch_range_validity": _metric_float(metrics, "pitch_range_validity"),
            "part_detection_rate": _metric_float(metrics, "part_detection_rate"),
        },
        "warnings": warnings,
        "stats": {
            "total_measures": _metric_int(metrics, "total_measures"),
            "total_notes": _metric_int(metrics, "total_notes"),
            "processing_time_seconds": _metric_float(metrics, "elapsed_seconds"),
        },
    }


def _judgment_from_result(result: object) -> str:
    metrics = _result_metrics(result)
    if metrics:
        return str(metrics.get("judgment", "PASS"))
    return "PASS"


def _resolve_quality_result_judgment(result: object, thresholds: QualityThresholds) -> str:
    metrics = _result_metrics(result)
    value = metrics.get("overall_score")
    if isinstance(value, (int, float)):
        return _judgment_from_score(float(value), thresholds)
    return _judgment_from_result(result)


def _judgment_from_score(overall_score: float, thresholds: QualityThresholds) -> str:
    if overall_score >= thresholds.pass_threshold:
        return "PASS"
    if overall_score >= thresholds.warn_threshold:
        return "REVIEW"
    return "FAIL"


def _result_metrics(result: object) -> dict[str, object]:
    metrics = getattr(result, "metrics", {})
    if isinstance(metrics, dict):
        return metrics
    return {}


def _warnings_from_result(result: object) -> list[str]:
    warnings = getattr(result, "warnings", [])
    if isinstance(warnings, list):
        return [str(item) for item in warnings]
    return []


def _metric_float(metrics: object, key: str) -> float:
    if isinstance(metrics, dict):
        value = metrics.get(key, 0.0)
        if isinstance(value, (int, float)):
            return float(value)
    return 0.0


def _metric_int(metrics: object, key: str) -> int:
    if isinstance(metrics, dict):
        value = metrics.get(key, 0)
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
    return 0


def _worst_judgment(judgments: Sequence[str]) -> str:
    if any(judgment == "FAIL" for judgment in judgments):
        return "FAIL"
    if any(judgment == "REVIEW" for judgment in judgments):
        return "REVIEW"
    return "PASS"


def _resolve_quality_thresholds(
    cli_config: CliPipelineConfig,
    quality_threshold: float | None,
) -> QualityThresholds:
    pass_threshold = cli_config.quality.pass_threshold if quality_threshold is None else quality_threshold
    warn_threshold = min(cli_config.quality.warn_threshold, pass_threshold)
    return QualityThresholds(pass_threshold=pass_threshold, warn_threshold=warn_threshold)


def _load_tuning(tuning_name: str) -> list[int]:
    return GuitarFixer.load_tuning(tuning_name)


def _exit_code_from_judgment(judgment: str) -> int:
    if judgment == "PASS":
        return 0
    if judgment == "REVIEW":
        return 1
    if judgment == "FAIL":
        return 2
    return 3


if __name__ == "__main__":
    raise SystemExit(main())