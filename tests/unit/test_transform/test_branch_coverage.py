"""branch coverage tests for transform helpers and fallback paths."""

from __future__ import annotations

from pathlib import Path
import zipfile

import pytest
from lxml import etree

from pipeline.transform.confidence_filter import ConfidenceFilter, FilterResult
from pipeline.transform.errors import TransformValidationError
from pipeline.transform.guitar_fixer import GuitarFixer, STANDARD_TUNING
from pipeline.transform.part_identifier import PartIdentifier
from pipeline.transform.validator import MusicXmlValidator


def _parse_tree(content: str) -> etree._ElementTree:
    return etree.ElementTree(etree.fromstring(content.encode("utf-8")))


class TestConfidenceFilterBranches:
    def test_filter_rate_is_zero_when_total_is_zero(self) -> None:
        result = FilterResult(tree=_parse_tree("<score-partwise version=\"4.0\" />"), total=0)

        assert result.filter_rate == 0.0

    def test_string_value_handles_empty_list_and_none(self) -> None:
        assert ConfidenceFilter._string_value([]) == ""
        assert ConfidenceFilter._string_value(None) == ""


class TestGuitarFixerBranches:
    def test_load_tuning_falls_back_for_invalid_structures(self, tmp_path: Path) -> None:
        config_path = tmp_path / "instrument_map.yaml"
        config_path.write_text("[]", encoding="utf-8")
        assert GuitarFixer.load_tuning("standard", config_path) == STANDARD_TUNING

        config_path.write_text("tunings: []", encoding="utf-8")
        assert GuitarFixer.load_tuning("standard", config_path) == STANDARD_TUNING

        config_path.write_text("tunings:\n  broken: [40, 45, 50]\n", encoding="utf-8")
        assert GuitarFixer.load_tuning("broken", config_path) == STANDARD_TUNING

        config_path.write_text(
            "tunings:\n  broken: [40, 45, 50, 55, 59, bad]\n",
            encoding="utf-8",
        )
        assert GuitarFixer.load_tuning("broken", config_path) == STANDARD_TUNING

    def test_collect_measure_notes_handles_rests_and_chords(self) -> None:
        measure = _parse_tree(
            """
<measure number="1">
  <note>
    <rest />
    <duration>1</duration>
    <voice>1</voice>
    <staff>1</staff>
  </note>
  <note>
    <pitch><step>C</step><octave>4</octave></pitch>
    <duration>1</duration>
    <voice>1</voice>
    <staff>1</staff>
  </note>
  <note>
    <chord />
    <pitch><step>E</step><octave>4</octave></pitch>
    <duration>1</duration>
    <voice>1</voice>
    <staff>1</staff>
  </note>
  <note>
    <duration>1</duration>
    <voice>1</voice>
    <staff>2</staff>
    <notations>
      <technical><string>1</string><fret>3</fret></technical>
    </notations>
  </note>
</measure>
""".strip()
        ).getroot()

        standard_notes, tab_notes = GuitarFixer._collect_measure_notes(
            measure,
            "P1",
            "1",
            {"2"},
        )

        assert len(standard_notes) == 2
        assert len(tab_notes) == 1
        assert ("P1", "1", "1", 1) in standard_notes

    def test_replace_pitch_creates_pitch_and_handles_alter_branches(self) -> None:
        note = etree.fromstring("<note><duration>1</duration></note>")
        GuitarFixer._replace_pitch(note, 61)

        assert note.xpath("string(./*[local-name()='pitch']/*[local-name()='step'])") == "C"
        assert note.xpath("string(./*[local-name()='pitch']/*[local-name()='alter'])") == "1"
        assert note.xpath("string(./*[local-name()='pitch']/*[local-name()='octave'])") == "4"

        note_with_alter = etree.fromstring(
            "<note><pitch><step>F</step><alter>1</alter><octave>4</octave></pitch></note>"
        )
        GuitarFixer._replace_pitch(note_with_alter, 60)

        assert note_with_alter.xpath("string(./*[local-name()='pitch']/*[local-name()='step'])") == "C"
        assert note_with_alter.xpath("count(./*[local-name()='pitch']/*[local-name()='alter'])") == 0.0

    def test_string_value_handles_empty_list_and_none(self) -> None:
        assert GuitarFixer._string_value([]) == ""
        assert GuitarFixer._string_value(None) == ""


class TestPartIdentifierBranches:
    def test_detect_tab_staff_uses_sign_attribute_default_number(self) -> None:
        part = _parse_tree(
            """
<part id="P1">
  <measure number="1">
    <attributes>
      <clef sign="TAB"><line>5</line></clef>
    </attributes>
  </measure>
</part>
""".strip()
        ).getroot()

        assert PartIdentifier._detect_tab_staff(part) == "1"

    def test_string_value_handles_empty_list_and_none(self) -> None:
        assert PartIdentifier._string_value([]) == ""
        assert PartIdentifier._string_value(None) == ""


class TestValidatorBranches:
    def test_validate_raises_when_mxl_contains_no_xml_file(self, tmp_path: Path) -> None:
        mxl_path = tmp_path / "no_xml.mxl"
        with zipfile.ZipFile(mxl_path, "w") as archive:
            archive.writestr("META-INF/container.txt", "missing xml")

        with pytest.raises(TransformValidationError, match="XML ファイルが見つかりません"):
            MusicXmlValidator.validate(mxl_path)

    def test_validate_raises_when_mxl_embedded_xml_is_invalid(self, tmp_path: Path) -> None:
        mxl_path = tmp_path / "invalid_xml.mxl"
        with zipfile.ZipFile(mxl_path, "w") as archive:
            archive.writestr("score.xml", "<score-partwise><part></score-partwise>")

        with pytest.raises(TransformValidationError, match="well-formed"):
            MusicXmlValidator.validate(mxl_path)

    def test_count_staves_falls_back_to_staves_value_then_part_count(self) -> None:
        tree_with_staves = _parse_tree(
            """
<score-partwise version="4.0">
  <part-list><score-part id="P1"><part-name>Guitar</part-name></score-part></part-list>
  <part id="P1"><measure number="1"><attributes><staves>3</staves></attributes></measure></part>
</score-partwise>
""".strip()
        )
        tree_with_parts_only = _parse_tree(
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

        assert MusicXmlValidator._count_staves(tree_with_staves) == 3
        assert MusicXmlValidator._count_staves(tree_with_parts_only) == 2

    def test_local_name_handles_bytes_and_namespaced_tags(self) -> None:
        namespaced_tag = "{urn:test}score-partwise"

        assert MusicXmlValidator._local_name(b"score-partwise") == "score-partwise"
        assert MusicXmlValidator._local_name(namespaced_tag) == "score-partwise"