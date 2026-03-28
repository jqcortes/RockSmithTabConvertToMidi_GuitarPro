"""GuitarFixer - apply TAB fret data to staff pitch notes."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from lxml import etree

from pipeline.common import get_logger
from pipeline.transform.tab_ocr import TabOcrToken

STANDARD_TUNING: list[int] = [40, 45, 50, 55, 59, 64]

_LOGGER = get_logger(__name__)
_DEFAULT_CONFIG_PATH = Path("config/instrument_map.yaml")
_PITCH_CLASSES: list[tuple[str, int]] = [
    ("C", 0),
    ("C", 1),
    ("D", 0),
    ("D", 1),
    ("E", 0),
    ("F", 0),
    ("F", 1),
    ("G", 0),
    ("G", 1),
    ("A", 0),
    ("A", 1),
    ("B", 0),
]


@dataclass(frozen=True)
class FixerResult:
    """Result of applying TAB correction to a MusicXML tree."""

    tree: etree._ElementTree
    applied: int
    skipped: int
    ocr_applied: int = 0
    ocr_skipped: int = 0


class GuitarFixer:
    """Apply TAB-derived pitch corrections to standard staff notes."""

    @staticmethod
    def apply(
        tree: etree._ElementTree,
        tuning: list[int] | None = None,
        ocr_tokens: Sequence[TabOcrToken] | None = None,
    ) -> FixerResult:
        """Apply TAB fret/string data to matching standard notes."""
        actual_tuning = list(tuning) if tuning is not None else list(STANDARD_TUNING)
        tab_staffs_by_part = GuitarFixer._detect_tab_staffs(tree)
        if not any(tab_staffs_by_part.values()):
            _LOGGER.info("guitar_fixer_no_tab_staff", applied=0, skipped=0)
            return FixerResult(tree=tree, applied=0, skipped=0)

        applied = 0
        skipped = 0
        ocr_applied = 0
        ocr_skipped = 0
        ocr_override_map = GuitarFixer._build_ocr_override_map(tree, ocr_tokens or [])

        for part in tree.xpath("//*[local-name()='part']"):
            part_id = GuitarFixer._string_value(part.xpath("@id"))
            tab_staffs = tab_staffs_by_part.get(part_id, set())
            if not tab_staffs:
                continue

            for measure in part.xpath("./*[local-name()='measure']"):
                measure_number = GuitarFixer._string_value(measure.xpath("@number"))
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

                    fret_text = GuitarFixer._string_value(
                        tab_note.xpath(
                            "./*[local-name()='notations']/*[local-name()='technical']/*[local-name()='fret']/text()"
                        )
                    )
                    string_text = GuitarFixer._string_value(
                        tab_note.xpath(
                            "./*[local-name()='notations']/*[local-name()='technical']/*[local-name()='string']/text()"
                        )
                    )

                    override = ocr_override_map.get(note_key)
                    used_ocr_override = False
                    if (not fret_text.isdigit() or not string_text.isdigit()) and override is not None:
                        string_text = str(override[0])
                        fret_text = str(override[1])
                        GuitarFixer._set_tab_technical(tab_note, string_text=string_text, fret_text=fret_text)
                        used_ocr_override = True

                    if not fret_text.isdigit() or not string_text.isdigit():
                        skipped += 1
                        if override is not None:
                            ocr_skipped += 1
                        continue

                    midi_pitch = GuitarFixer.fret_to_pitch(
                        int(string_text),
                        int(fret_text),
                        actual_tuning,
                    )
                    GuitarFixer._replace_pitch(standard_note, midi_pitch)
                    applied += 1
                    if used_ocr_override:
                        ocr_applied += 1

        _LOGGER.info(
            "guitar_fixer_applied",
            applied=applied,
            skipped=skipped,
            ocr_applied=ocr_applied,
            ocr_skipped=ocr_skipped,
        )
        return FixerResult(
            tree=tree,
            applied=applied,
            skipped=skipped,
            ocr_applied=ocr_applied,
            ocr_skipped=ocr_skipped,
        )

    @staticmethod
    def fret_to_pitch(string: int, fret: int, tuning: list[int]) -> int:
        """Convert string/fret into MIDI pitch number."""
        return tuning[6 - string] + fret

    @staticmethod
    def load_tuning(name: str, config_path: Path | None = None) -> list[int]:
        """Load tuning from YAML config or return standard tuning fallback."""
        actual_path = config_path if config_path is not None else _DEFAULT_CONFIG_PATH
        if not actual_path.exists():
            return list(STANDARD_TUNING)

        try:
            content = yaml.safe_load(actual_path.read_text(encoding="utf-8"))
        except OSError:
            return list(STANDARD_TUNING)

        if not isinstance(content, dict):
            return list(STANDARD_TUNING)
        tunings = content.get("tunings")
        if not isinstance(tunings, dict):
            return list(STANDARD_TUNING)
        value = tunings.get(name)
        if not isinstance(value, list) or len(value) != 6:
            return list(STANDARD_TUNING)

        try:
            return [int(item) for item in value]
        except (TypeError, ValueError):
            return list(STANDARD_TUNING)

    @staticmethod
    def _detect_tab_staffs(tree: etree._ElementTree) -> dict[str, set[str]]:
        """Detect TAB staff numbers for each part."""
        result: dict[str, set[str]] = {}
        for part in tree.xpath("//*[local-name()='part']"):
            part_id = GuitarFixer._string_value(part.xpath("@id"))
            staff_numbers: set[str] = set()
            for details in part.xpath(
                ".//*[local-name()='staff-details'][number(*[local-name()='staff-lines'])=6]"
            ):
                number = GuitarFixer._string_value(details.xpath("@number"))
                if number:
                    staff_numbers.add(number)
            for clef in part.xpath(".//*[local-name()='clef']"):
                sign_text = GuitarFixer._string_value(
                    clef.xpath("./*[local-name()='sign']/text()")
                ).upper()
                sign_attr = GuitarFixer._string_value(clef.xpath("@sign")).upper()
                if sign_text == "TAB" or sign_attr == "TAB":
                    number = GuitarFixer._string_value(clef.xpath("@number")) or "1"
                    staff_numbers.add(number)
            result[part_id] = staff_numbers
        return result

    @staticmethod
    def _collect_measure_notes(
        measure: Any,
        part_id: str,
        measure_number: str,
        tab_staffs: set[str],
    ) -> tuple[dict[tuple[str, str, str, int], Any], dict[tuple[str, str, str, int], Any]]:
        """Collect standard and TAB notes indexed by part/measure/voice/offset."""
        standard_notes: dict[tuple[str, str, str, int], Any] = {}
        tab_notes: dict[tuple[str, str, str, int], Any] = {}
        offsets: dict[tuple[str, str], int] = {}

        for note in measure.xpath("./*[local-name()='note']"):
            staff = GuitarFixer._string_value(note.xpath("./*[local-name()='staff']/text()")) or "1"
            voice = GuitarFixer._string_value(note.xpath("./*[local-name()='voice']/text()")) or "1"
            duration_text = GuitarFixer._string_value(note.xpath("./*[local-name()='duration']/text()"))
            duration = int(duration_text) if duration_text.isdigit() else 0
            offset_key = (staff, voice)
            offset = offsets.get(offset_key, 0)
            note_key = (part_id, measure_number, voice, offset)

            if note.xpath("./*[local-name()='rest']"):
                offsets[offset_key] = offset + duration
                continue

            if staff in tab_staffs:
                tab_notes[note_key] = note
            elif note.xpath("./*[local-name()='pitch']"):
                standard_notes[note_key] = note

            if not note.xpath("./*[local-name()='chord']"):
                offsets[offset_key] = offset + duration

        return standard_notes, tab_notes

    @staticmethod
    def _replace_pitch(note: Any, midi_pitch: int) -> None:
        """Replace MusicXML pitch children for the provided note."""
        step, alter, octave = GuitarFixer._midi_to_pitch_components(midi_pitch)
        pitch_nodes = note.xpath("./*[local-name()='pitch']")
        pitch = pitch_nodes[0] if pitch_nodes else etree.SubElement(note, "pitch")

        GuitarFixer._set_child_text(pitch, "step", step)
        if alter == 0:
            for alter_node in pitch.xpath("./*[local-name()='alter']"):
                pitch.remove(alter_node)
        else:
            GuitarFixer._set_child_text(pitch, "alter", str(alter))
        GuitarFixer._set_child_text(pitch, "octave", str(octave))

    @staticmethod
    def _midi_to_pitch_components(midi_pitch: int) -> tuple[str, int, int]:
        """Convert MIDI pitch number into MusicXML step/alter/octave."""
        pitch_class = midi_pitch % 12
        step, alter = _PITCH_CLASSES[pitch_class]
        octave = (midi_pitch // 12) - 1
        return step, alter, octave

    @staticmethod
    def _set_child_text(parent: Any, name: str, value: str) -> None:
        """Set or create a child element text value."""
        children = parent.xpath(f"./*[local-name()='{name}']")
        if children:
            children[0].text = value
            return
        child = etree.SubElement(parent, name)
        child.text = value

    @staticmethod
    def _set_tab_technical(note: Any, *, string_text: str, fret_text: str) -> None:
        """Ensure TAB note has technical/string/fret nodes for downstream use."""
        notations_nodes = note.xpath("./*[local-name()='notations']")
        notations = notations_nodes[0] if notations_nodes else etree.SubElement(note, "notations")

        technical_nodes = notations.xpath("./*[local-name()='technical']")
        if technical_nodes:
            technical = technical_nodes[0]
        else:
            technical = etree.SubElement(notations, "technical")

        GuitarFixer._set_child_text(technical, "string", string_text)
        GuitarFixer._set_child_text(technical, "fret", fret_text)

    @staticmethod
    def _build_ocr_override_map(
        tree: etree._ElementTree,
        ocr_tokens: Sequence[TabOcrToken],
    ) -> dict[tuple[str, str, str, int], tuple[int, int]]:
        """Map OCR fret tokens onto TAB notes in document order.

        The MVP strategy is intentionally conservative: OCR tokens are only used
        when the token count exactly matches the number of TAB notes on the page.
        """
        if len(ocr_tokens) == 0:
            return {}

        tab_notes = GuitarFixer._collect_all_tab_notes(tree)
        if len(tab_notes) != len(ocr_tokens):
            _LOGGER.warning(
                "guitar_fixer_ocr_count_mismatch",
                tab_notes=len(tab_notes),
                ocr_tokens=len(ocr_tokens),
            )
            return {}

        override_map: dict[tuple[str, str, str, int], tuple[int, int]] = {}
        for (note_key, _note), token in zip(tab_notes, ocr_tokens, strict=True):
            override_map[note_key] = (token.string, token.fret)
        return override_map

    @staticmethod
    def _collect_all_tab_notes(
        tree: etree._ElementTree,
    ) -> list[tuple[tuple[str, str, str, int], Any]]:
        """Return all TAB notes in document order using the same note-key scheme."""
        tab_notes: list[tuple[tuple[str, str, str, int], Any]] = []
        tab_staffs_by_part = GuitarFixer._detect_tab_staffs(tree)
        for part in tree.xpath("//*[local-name()='part']"):
            part_id = GuitarFixer._string_value(part.xpath("@id"))
            tab_staffs = tab_staffs_by_part.get(part_id, set())
            if not tab_staffs:
                continue

            for measure in part.xpath("./*[local-name()='measure']"):
                measure_number = GuitarFixer._string_value(measure.xpath("@number"))
                _standard_notes, measure_tab_notes = GuitarFixer._collect_measure_notes(
                    measure,
                    part_id,
                    measure_number,
                    tab_staffs,
                )
                tab_notes.extend(measure_tab_notes.items())
        return tab_notes

    @staticmethod
    def _string_value(value: Any) -> str:
        """Normalize xpath/string results into a plain string."""
        if isinstance(value, list):
            if not value:
                return ""
            return GuitarFixer._string_value(value[0])
        if value is None:
            return ""
        return str(value).strip()
