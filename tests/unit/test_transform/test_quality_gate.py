"""tests for transform quality gate helper behavior."""

from __future__ import annotations

from pathlib import Path

from lxml import etree

from pipeline.transform._transform import (
    _evaluate_quality_gate,
    _has_any_tab_staff,
    _has_measure_inconsistency,
    _has_pitch_tab_conflict,
    _pitch_to_midi,
    _removed_note_warning,
    _string_value,
)
from pipeline.transform.confidence_filter import RemovedNote
from pipeline.transform.validator import ValidationResult


FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "musicxml"


def _parse_tree(content: str) -> etree._ElementTree:
    return etree.ElementTree(etree.fromstring(content.encode("utf-8")))


class TestQualityGateHelpers:
    def test_evaluate_quality_gate_returns_missing_tab_and_part_info_reasons(self) -> None:
        tree = etree.parse(str(FIXTURES_DIR / "transform_missing_part_info.xml"))
        validation_result = ValidationResult(tree=tree, part_count=1, measure_count=1, staff_count=1)

        fallback_required, reasons = _evaluate_quality_gate(validation_result)

        assert fallback_required is True
        assert reasons == ["part_info_missing", "tab_staff_missing"]

    def test_evaluate_quality_gate_detects_measure_inconsistency(self) -> None:
        tree = etree.parse(str(FIXTURES_DIR / "transform_measure_inconsistent.xml"))
        validation_result = ValidationResult(tree=tree, part_count=2, measure_count=3, staff_count=2)

        fallback_required, reasons = _evaluate_quality_gate(validation_result)

        assert fallback_required is True
        assert "measure_inconsistent" in reasons

    def test_evaluate_quality_gate_detects_pitch_tab_conflict(self) -> None:
        tree = etree.parse(str(FIXTURES_DIR / "transform_pitch_conflict.xml"))
        validation_result = ValidationResult(tree=tree, part_count=1, measure_count=1, staff_count=2)

        fallback_required, reasons = _evaluate_quality_gate(validation_result)

        assert fallback_required is True
        assert "pitch_tab_conflict" in reasons

    def test_evaluate_quality_gate_passes_clean_tab_score(self) -> None:
        tree = etree.parse(str(FIXTURES_DIR / "transform_clean_tab.xml"))
        validation_result = ValidationResult(tree=tree, part_count=1, measure_count=1, staff_count=2)

        fallback_required, reasons = _evaluate_quality_gate(validation_result)

        assert fallback_required is False
        assert reasons == []

    def test_has_any_tab_staff_and_measure_inconsistency_helpers(self) -> None:
        tree_with_tab = _parse_tree(
            """
<score-partwise version="4.0">
  <part-list><score-part id="P1"><part-name>Lead Guitar</part-name></score-part></part-list>
  <part id="P1"><measure number="1"><attributes><clef sign="TAB" /></attributes></measure></part>
</score-partwise>
""".strip()
        )
        balanced_tree = _parse_tree(
            """
<score-partwise version="4.0">
  <part-list>
    <score-part id="P1"><part-name>One</part-name></score-part>
    <score-part id="P2"><part-name>Two</part-name></score-part>
  </part-list>
  <part id="P1"><measure number="1" /></part>
  <part id="P2"><measure number="1" /></part>
</score-partwise>
""".strip()
        )

        assert _has_any_tab_staff(tree_with_tab) is True
        assert _has_measure_inconsistency(balanced_tree) is False

    def test_has_pitch_tab_conflict_false_when_matching_or_missing_pitch(self) -> None:
        matching_tree = _parse_tree(
            """
<score-partwise version="4.0">
  <part-list><score-part id="P1"><part-name>Lead Guitar</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <staves>2</staves>
        <staff-details number="2"><staff-lines>6</staff-lines></staff-details>
      </attributes>
      <note><pitch><step>G</step><octave>4</octave></pitch><duration>2</duration><voice>1</voice><staff>1</staff></note>
      <note><duration>2</duration><voice>1</voice><staff>2</staff><notations><technical><string>1</string><fret>3</fret></technical></notations></note>
    </measure>
  </part>
</score-partwise>
""".strip()
        )
        missing_pitch_tree = _parse_tree(
            """
<score-partwise version="4.0">
  <part-list><score-part id="P1"><part-name>Lead Guitar</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <staves>2</staves>
        <staff-details number="2"><staff-lines>6</staff-lines></staff-details>
      </attributes>
      <note><duration>2</duration><voice>1</voice><staff>1</staff></note>
      <note><duration>2</duration><voice>1</voice><staff>2</staff><notations><technical><string>1</string><fret>3</fret></technical></notations></note>
    </measure>
  </part>
</score-partwise>
""".strip()
        )

        assert _has_pitch_tab_conflict(matching_tree) is False
        assert _has_pitch_tab_conflict(missing_pitch_tree) is False

    def test_pitch_to_midi_and_string_helpers_cover_fallback_cases(self) -> None:
        note = etree.fromstring("<note><pitch><step>F</step><alter>1</alter><octave>4</octave></pitch></note>")
        invalid_step = etree.fromstring("<note><pitch><step>H</step><octave>4</octave></pitch></note>")
        missing_octave = etree.fromstring("<note><pitch><step>C</step></pitch></note>")

        assert _pitch_to_midi(note) == 66
        assert _pitch_to_midi(invalid_step) is None
        assert _pitch_to_midi(missing_octave) is None
        assert _string_value([" test "]) == "test"
        assert _string_value(None) == ""

    def test_removed_note_warning_format(self) -> None:
        warning = _removed_note_warning(
            RemovedNote(measure="2", part_id="P1", pitch="E4", confidence=0.25)
        )

        assert warning == "Filtered note: part=P1 measure=2 pitch=E4 confidence=0.25"