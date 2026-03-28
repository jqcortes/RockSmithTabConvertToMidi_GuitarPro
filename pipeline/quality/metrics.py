"""Quality metrics calculation for the Quality domain."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from lxml import etree

PartRole = Literal["guitar", "bass", "drums", "other"]
GUITAR_RANGE = (40, 88)
BASS_RANGE = (28, 67)
_MEASURE_TOLERANCE = 0.125


@dataclass(frozen=True)
class QualityMetrics:
    """Calculated quality metrics and supporting warning/stat data."""

    omr_confidence: float
    measure_completeness: float
    pitch_range_validity: float
    part_detection_rate: float
    warnings: list[dict[str, str]]
    total_measures: int
    total_notes: int


class QualityMetricsCalculator:
    """Calculate quality metrics from transformed MusicXML."""

    @staticmethod
    def calculate(tree: etree._ElementTree, expected_parts: list[str] | None = None) -> QualityMetrics:
        """Calculate the four quality metrics plus warnings and aggregate stats."""
        measure_completeness, measure_warnings, total_measures = _measure_completeness(tree)
        pitch_range_validity, pitch_warnings, total_notes = _pitch_range_validity(tree)
        detected_roles = _detected_roles(tree)
        part_detection_rate = _part_detection_rate(detected_roles, expected_parts)
        omr_confidence = _omr_confidence(tree)

        return QualityMetrics(
            omr_confidence=omr_confidence,
            measure_completeness=measure_completeness,
            pitch_range_validity=pitch_range_validity,
            part_detection_rate=part_detection_rate,
            warnings=[*measure_warnings, *pitch_warnings],
            total_measures=total_measures,
            total_notes=total_notes,
        )


def _omr_confidence(tree: etree._ElementTree) -> float:
    values = [
        max(0.0, min(1.0, float(value)))
        for value in tree.xpath("//*[@confidence]/@confidence")
        if _is_float(str(value))
    ]
    if values:
        return round(sum(values) / len(values), 3)

    # Audiveris does not embed per-note confidence in MusicXML output.
    # Estimate OMR confidence from structural signals in the score:
    #   1. Note density: notes per measure (higher = richer recognition)
    #   2. Tempo/metronome marks present (score structure well-parsed)
    #   3. Key/time signatures present (headers read correctly)
    parts = tree.xpath("//*[local-name()='part']")
    total_measures = sum(len(p.xpath("./*[local-name()='measure']")) for p in parts)
    total_notes = sum(
        len(m.xpath("./*[local-name()='note']"))
        for p in parts
        for m in p.xpath("./*[local-name()='measure']")
    )
    notes_per_measure = total_notes / total_measures if total_measures > 0 else 0

    # Base confidence from note density: 0 n/m → 0.50, 5+ n/m → 0.90
    density_score = min(0.90, 0.50 + notes_per_measure * 0.08)

    # Bonus signals
    has_tempo = bool(
        tree.xpath("//*[local-name()='sound'][@tempo]")
        or tree.xpath("//*[local-name()='direction-type']/*[local-name()='metronome']")
    )
    has_time_sig = bool(tree.xpath("//*[local-name()='time']/*[local-name()='beats']"))
    has_key_sig = bool(tree.xpath("//*[local-name()='key']/*[local-name()='fifths']"))

    bonus = (0.03 if has_tempo else 0.0) + (0.02 if has_time_sig else 0.0) + (0.02 if has_key_sig else 0.0)

    return round(min(1.0, density_score + bonus), 3)


def _measure_completeness(tree: etree._ElementTree) -> tuple[float, list[dict[str, str]], int]:
    warnings: list[dict[str, str]] = []
    total = 0
    valid_sum = 0.0

    for part in tree.xpath("//*[local-name()='part']"):
        # Skip parts that have no real (non-rest) notes — they are silent on this page.
        all_part_notes = part.xpath(".//*[local-name()='note']")
        has_real_note = any(
            not n.xpath("./*[local-name()='rest']") for n in all_part_notes
        )
        if not has_real_note:
            continue

        part_name = _part_name(tree, _string_value(part.xpath("@id")))
        current_time = (4, 4)
        current_divisions = 1
        for measure in part.xpath("./*[local-name()='measure']"):
            current_divisions = _measure_divisions(measure, current_divisions)
            current_time = _measure_time_signature(measure, current_time)

            expected = current_time[0] * (4.0 / current_time[1])
            actual = 0.0
            for note in measure.xpath("./*[local-name()='note']"):
                # Skip chord notes: they share timing with the previous note
                # and must not be added to the measure duration total.
                if note.xpath("./*[local-name()='chord']"):
                    continue
                duration_text = _string_value(note.xpath("./*[local-name()='duration']/text()"))
                if duration_text.isdigit():
                    actual += int(duration_text) / current_divisions

            # Skip measures with no notes at all (silent measure within active part)
            if actual == 0.0 and not measure.xpath("./*[local-name()='note']"):
                continue

            total += 1
            if abs(actual - expected) <= _MEASURE_TOLERANCE:
                valid_sum += 1.0
            else:
                # Proportional credit: penalise over/under-filled measures gradually.
                credit = min(actual, expected) / expected if expected > 0 else 0.0
                valid_sum += credit
                warnings.append(
                    {
                        "type": "MEASURE_INCOMPLETE",
                        "location": f"Part: {part_name}, Measure: {_string_value(measure.xpath('@number')) or '1'}",
                        "detail": f"Expected {expected:.1f} beats, found {actual:.1f}",
                    }
                )

    if total == 0:
        return 0.0, warnings, 0
    return round(valid_sum / total, 3), warnings, total


def _pitch_range_validity(tree: etree._ElementTree) -> tuple[float, list[dict[str, str]], int]:
    warnings: list[dict[str, str]] = []
    total_notes = 0
    valid_notes = 0

    for part in tree.xpath("//*[local-name()='part']"):
        part_id = _string_value(part.xpath("@id"))
        part_name = _part_name(tree, part_id)
        role = _part_role(part, part_name)
        for measure in part.xpath("./*[local-name()='measure']"):
            measure_number = _string_value(measure.xpath("@number")) or "1"
            for note in measure.xpath("./*[local-name()='note']"):
                if note.xpath("./*[local-name()='rest']"):
                    continue
                midi_note = _pitch_to_midi(note)
                if midi_note is None:
                    continue

                total_notes += 1
                if _note_in_range(midi_note, role):
                    valid_notes += 1
                    continue

                warnings.append(
                    {
                        "type": "PITCH_OUT_OF_RANGE",
                        "location": f"Part: {part_name}, Measure: {measure_number}",
                        "detail": f"MIDI note {midi_note} is outside expected range for {role}",
                    }
                )

    if total_notes == 0:
        return 0.0, warnings, 0
    return round(valid_notes / total_notes, 3), warnings, total_notes


def _part_detection_rate(detected_roles: list[str], expected_parts: list[str] | None) -> float:
    expected = [role.lower() for role in expected_parts] if expected_parts is not None else detected_roles
    if not expected:
        return 0.0
    matched = sum(1 for expected_role in expected if expected_role in detected_roles)
    return round(matched / len(expected), 3)


def _detected_roles(tree: etree._ElementTree) -> list[str]:
    roles: list[str] = []
    for part in tree.xpath("//*[local-name()='part']"):
        part_name = _part_name(tree, _string_value(part.xpath("@id")))
        role = _part_role(part, part_name)
        if role not in roles:
            roles.append(role)
    return roles


def _part_role(part: etree._Element, part_name: str) -> PartRole:
    role = _string_value(part.xpath("@*[local-name()='role']")).lower()
    if role in {"guitar", "bass", "drums", "other"}:
        return role  # type: ignore[return-value]
    lowered = part_name.lower()
    if "guitar" in lowered:
        return "guitar"
    if "bass" in lowered:
        return "bass"
    if "drum" in lowered or "perc" in lowered:
        return "drums"
    return "other"


def _part_name(tree: etree._ElementTree, part_id: str) -> str:
    value = tree.xpath(
        "//*[local-name()='part-list']/*[local-name()='score-part'][@id=$part_id]/*[local-name()='part-name']/text()",
        part_id=part_id,
    )
    name = _string_value(value)
    return name or part_id or "Unknown"


def _measure_divisions(measure: etree._Element, current_divisions: int) -> int:
    divisions_text = _string_value(measure.xpath("./*[local-name()='attributes']/*[local-name()='divisions']/text()"))
    if divisions_text.isdigit():
        return max(1, int(divisions_text))
    return current_divisions


def _measure_time_signature(measure: etree._Element, current_time: tuple[int, int]) -> tuple[int, int]:
    beats_text = _string_value(measure.xpath("./*[local-name()='attributes']/*[local-name()='time']/*[local-name()='beats']/text()"))
    beat_type_text = _string_value(
        measure.xpath("./*[local-name()='attributes']/*[local-name()='time']/*[local-name()='beat-type']/text()")
    )
    if beats_text.isdigit() and beat_type_text.isdigit():
        return int(beats_text), int(beat_type_text)
    return current_time


def _note_in_range(midi_note: int, role: PartRole) -> bool:
    if role == "drums":
        return True
    if role == "bass":
        return BASS_RANGE[0] <= midi_note <= BASS_RANGE[1]
    return GUITAR_RANGE[0] <= midi_note <= GUITAR_RANGE[1]


def _pitch_to_midi(note: etree._Element) -> int | None:
    step = _string_value(note.xpath("./*[local-name()='pitch']/*[local-name()='step']/text()"))
    octave_text = _string_value(note.xpath("./*[local-name()='pitch']/*[local-name()='octave']/text()"))
    alter_text = _string_value(note.xpath("./*[local-name()='pitch']/*[local-name()='alter']/text()"))
    if step == "" or not octave_text.lstrip("-").isdigit():
        return None

    offsets = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
    offset = offsets.get(step.upper())
    if offset is None:
        return None

    alter = int(alter_text) if alter_text.lstrip("-").isdigit() else 0
    octave = int(octave_text)
    return ((octave + 1) * 12) + offset + alter


def _string_value(value: object) -> str:
    if isinstance(value, list):
        if not value:
            return ""
        return _string_value(value[0])
    if value is None:
        return ""
    return str(value).strip()


def _is_float(value: str) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    return True