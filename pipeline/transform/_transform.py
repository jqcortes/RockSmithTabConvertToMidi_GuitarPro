"""transform() - Transform ドメインの公開エントリポイント。"""

from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import TypeAlias

from lxml import etree

from pipeline.common import MetricValue, StepResult, get_logger
from pipeline.transform.confidence_filter import ConfidenceFilter, RemovedNote
from pipeline.transform.errors import TransformError
from pipeline.transform.guitar_fixer import GuitarFixer, STANDARD_TUNING
from pipeline.transform.part_identifier import PartIdentifier
from pipeline.transform.validator import MusicXmlValidator, ValidationResult

GateResult: TypeAlias = tuple[bool, list[str]]


def transform(
    musicxml_path: Path,
    output_dir: Path,
    *,
    tuning: list[int] | None = None,
) -> StepResult:
    """Transform validated MusicXML into corrected cached output.

    Args:
        musicxml_path: OMR ドメインが出力した MusicXML / MXL パス。
        output_dir: 補正済み MusicXML の書き出し先ディレクトリ。

    Returns:
        success=True の StepResult。キャッシュヒット時は変換をスキップする。

    Raises:
        TransformError: Transform ドメイン固有例外、または予期しない失敗のラップ。
    """
    logger = get_logger(__name__)
    cached_output_path = _build_output_path(musicxml_path, output_dir)

    logger.info(
        "transform_start",
        musicxml_path=str(musicxml_path),
        output_dir=str(output_dir),
    )

    if cached_output_path.exists():
        logger.info("transform_cache_hit", output_path=str(cached_output_path))
        return StepResult.ok(
            output_path=cached_output_path,
            metrics={
                "cached": True,
                "elapsed_seconds": 0.0,
                "musicxml_path": str(cached_output_path),
            },
        )

    start_time = perf_counter()

    try:
        validation_result = MusicXmlValidator.validate(musicxml_path)
        fallback_required, fallback_reasons = _evaluate_quality_gate(validation_result)

        working_tree = validation_result.tree
        fixer_applied = 0
        fixer_skipped = 0
        filtered_notes = 0
        filter_rate = 0.0

        if fallback_required:
            fixer_result = GuitarFixer.apply(working_tree, tuning=tuning)
            working_tree = fixer_result.tree
            fixer_applied = fixer_result.applied
            fixer_skipped = fixer_result.skipped

        part_result = PartIdentifier.identify(working_tree)
        annotated_tree = PartIdentifier.annotate(working_tree, part_result)

        removed_notes: list[RemovedNote] = []
        if fallback_required:
            filter_result = ConfidenceFilter.filter(annotated_tree)
            annotated_tree = filter_result.tree
            removed_notes = filter_result.removed
            filtered_notes = len(filter_result.removed)
            filter_rate = filter_result.filter_rate

        output_dir.mkdir(parents=True, exist_ok=True)
        serialized_tree = etree.tostring(
            annotated_tree,
            encoding="unicode",
            pretty_print=True,
        )
        cached_output_path.write_text(serialized_tree, encoding="utf-8")

        elapsed_seconds = perf_counter() - start_time
        warnings = [
            *part_result.warnings,
            *[_removed_note_warning(note) for note in removed_notes],
        ]
        metrics: dict[str, MetricValue] = {
            "cached": False,
            "elapsed_seconds": elapsed_seconds,
            "musicxml_path": str(cached_output_path),
            "fallback_required": fallback_required,
            "fallback_reasons": fallback_reasons,
            "part_count": validation_result.part_count,
            "measure_count": validation_result.measure_count,
            "staff_count": validation_result.staff_count,
            "fixer_applied": fixer_applied,
            "fixer_skipped": fixer_skipped,
            "filtered_notes": filtered_notes,
            "filter_rate": filter_rate,
            "identified_parts": len(part_result.parts),
            "parts": {part_id: str(role) for part_id, role in part_result.parts_map.items()},
        }

        logger.info(
            "transform_complete",
            output_path=str(cached_output_path),
            elapsed_seconds=elapsed_seconds,
            fallback_required=fallback_required,
            fallback_reasons=fallback_reasons,
            fixer_applied=fixer_applied,
            filtered_notes=filtered_notes,
        )
        return StepResult.ok(
            output_path=cached_output_path,
            metrics=metrics,
            warnings=warnings,
        )
    except TransformError:
        logger.exception("transform_failed", musicxml_path=str(musicxml_path))
        raise
    except Exception as exc:
        logger.exception(
            "transform_unexpected_error",
            musicxml_path=str(musicxml_path),
        )
        raise TransformError(f"Unexpected transform failure: {exc}") from exc


def _build_output_path(musicxml_path: Path, output_dir: Path) -> Path:
    """Return the canonical cached output path for transformed MusicXML."""
    return output_dir / f"{musicxml_path.stem}_transformed.xml"


def _removed_note_warning(note: RemovedNote) -> str:
    """Format a removed-note warning for StepResult.warnings."""
    return (
        "Filtered note: "
        f"part={note.part_id} measure={note.measure} "
        f"pitch={note.pitch} confidence={note.confidence}"
    )


def _evaluate_quality_gate(validation_result: ValidationResult) -> GateResult:
    """Evaluate whether Audiveris output needs rescue processing."""
    tree = validation_result.tree
    reasons: list[str] = []

    if not tree.xpath("//*[local-name()='part-list']/*[local-name()='score-part']"):
        reasons.append("part_info_missing")

    if not _has_any_tab_staff(tree):
        reasons.append("tab_staff_missing")

    if _has_measure_inconsistency(tree):
        reasons.append("measure_inconsistent")

    if _has_pitch_tab_conflict(tree):
        reasons.append("pitch_tab_conflict")

    return bool(reasons), reasons


def _has_any_tab_staff(tree: etree._ElementTree) -> bool:
    return bool(
        tree.xpath(
            "//*[local-name()='clef'][@sign='TAB' or *[local-name()='sign']='TAB']"
            " | //*[local-name()='staff-details'][number(*[local-name()='staff-lines'])=6]"
        )
    )


def _has_measure_inconsistency(tree: etree._ElementTree) -> bool:
    measure_counts = [
        len(part.xpath("./*[local-name()='measure']"))
        for part in tree.xpath("//*[local-name()='part']")
    ]
    return len(set(measure_counts)) > 1 if measure_counts else False


def _has_pitch_tab_conflict(tree: etree._ElementTree) -> bool:
    for part in tree.xpath("//*[local-name()='part']"):
        part_id = _string_value(part.xpath("@id"))
        tab_staffs = GuitarFixer._detect_tab_staffs(etree.ElementTree(part)).get(part_id, set())
        if not tab_staffs:
            continue

        for measure in part.xpath("./*[local-name()='measure']"):
            measure_number = _string_value(measure.xpath("@number"))
            standard_notes, tab_notes = GuitarFixer._collect_measure_notes(
                measure,
                part_id,
                measure_number,
                tab_staffs,
            )
            for note_key, standard_note in standard_notes.items():
                tab_note = tab_notes.get(note_key)
                if tab_note is None:
                    continue

                fret_text = _string_value(
                    tab_note.xpath(
                        "./*[local-name()='notations']/*[local-name()='technical']/*[local-name()='fret']/text()"
                    )
                )
                string_text = _string_value(
                    tab_note.xpath(
                        "./*[local-name()='notations']/*[local-name()='technical']/*[local-name()='string']/text()"
                    )
                )
                if not fret_text.isdigit() or not string_text.isdigit():
                    continue

                expected_pitch = GuitarFixer.fret_to_pitch(
                    int(string_text),
                    int(fret_text),
                    list(STANDARD_TUNING),
                )
                current_pitch = _pitch_to_midi(standard_note)
                if current_pitch is not None and current_pitch != expected_pitch:
                    return True
    return False


def _pitch_to_midi(note: etree._Element) -> int | None:
    step = _string_value(note.xpath("string(./*[local-name()='pitch']/*[local-name()='step'])"))
    octave_text = _string_value(note.xpath("string(./*[local-name()='pitch']/*[local-name()='octave'])"))
    alter_text = _string_value(note.xpath("string(./*[local-name()='pitch']/*[local-name()='alter'])"))
    if step == "" or octave_text == "" or not octave_text.lstrip("-").isdigit():
        return None

    step_offsets = {
        "C": 0,
        "D": 2,
        "E": 4,
        "F": 5,
        "G": 7,
        "A": 9,
        "B": 11,
    }
    base_offset = step_offsets.get(step.upper())
    if base_offset is None:
        return None

    alter = int(alter_text) if alter_text not in {"", "-"} and alter_text.lstrip("-").isdigit() else 0
    octave = int(octave_text)
    return (octave + 1) * 12 + base_offset + alter


def _string_value(value: object) -> str:
    if isinstance(value, list):
        if not value:
            return ""
        return _string_value(value[0])
    if value is None:
        return ""
    return str(value).strip()