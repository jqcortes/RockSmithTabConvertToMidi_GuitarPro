"""render() - Render ドメインの公開エントリポイント。"""

from __future__ import annotations

from pathlib import Path
from time import perf_counter

from pipeline.common import MetricValue, StepResult, get_logger
from pipeline.render.errors import RenderError, RenderExecutionError
from pipeline.render.midi_renderer import MidiRenderer


def render(
    musicxml_path: Path,
    output_dir: Path,
    *,
    default_bpm: int = 120,
    pitch_bend_range: int = 2,
) -> StepResult:
    """Render transformed MusicXML to a cached MIDI Type 1 file."""
    logger = get_logger(__name__)
    output_path = output_dir / f"{musicxml_path.stem}.mid"

    logger.info("render_start", musicxml_path=str(musicxml_path), output_dir=str(output_dir))
    if output_path.exists():
        logger.info("render_cache_hit", output_path=str(output_path))
        return StepResult.ok(
            output_path=output_path,
            metrics={
                "cached": True,
                "elapsed_seconds": 0.0,
                "channel_map": {},
                "tempo_events": 0,
                "techniques_rendered": 0,
            },
        )

    started_at = perf_counter()
    try:
        result = MidiRenderer.render_score(
            musicxml_path,
            output_path,
            default_bpm=default_bpm,
            pitch_bend_range=pitch_bend_range,
        )
        elapsed_seconds = perf_counter() - started_at
        metrics: dict[str, MetricValue] = {
            "cached": False,
            "elapsed_seconds": elapsed_seconds,
            "channel_map": result.channel_map,
            "tempo_events": result.tempo_events,
            "techniques_rendered": result.techniques_rendered,
        }
        logger.info(
            "render_complete",
            output_path=str(result.output_path),
            elapsed_seconds=elapsed_seconds,
            tempo_events=result.tempo_events,
            techniques_rendered=result.techniques_rendered,
        )
        return StepResult.ok(output_path=result.output_path, metrics=metrics, warnings=result.warnings)
    except RenderError:
        logger.exception("render_failed", musicxml_path=str(musicxml_path))
        raise
    except Exception as exc:
        logger.exception("render_unexpected_error", musicxml_path=str(musicxml_path))
        raise RenderExecutionError(str(exc)) from exc