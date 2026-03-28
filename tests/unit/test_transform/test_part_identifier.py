"""tests for PartIdentifier."""

from __future__ import annotations

from lxml import etree


def _parse_xml(content: str) -> etree._ElementTree:
    return etree.ElementTree(etree.fromstring(content.encode("utf-8")))


class TestPartIdentifier:
    def test_identify_assigns_roles_and_detects_tab_staff(self) -> None:
        from pipeline.transform.part_identifier import PartIdentifier

        tree = _parse_xml(
            """
<score-partwise version="4.0">
  <part-list>
    <score-part id="P1">
      <part-name>Lead Guitar</part-name>
      <score-instrument id="P1-I1"><instrument-name>Lead Guitar</instrument-name></score-instrument>
    </score-part>
    <score-part id="P2">
      <part-name>Bass</part-name>
      <score-instrument id="P2-I1"><instrument-name>Bass Guitar</instrument-name></score-instrument>
    </score-part>
    <score-part id="P3">
      <part-name>Drums</part-name>
      <score-instrument id="P3-I1"><instrument-name>Drum Kit</instrument-name></score-instrument>
    </score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <staves>2</staves>
        <staff-details number="2"><staff-lines>6</staff-lines></staff-details>
        <clef number="2"><sign>TAB</sign><line>5</line></clef>
      </attributes>
    </measure>
  </part>
  <part id="P2">
    <measure number="1">
      <attributes>
        <staves>1</staves>
      </attributes>
    </measure>
  </part>
  <part id="P3">
    <measure number="1">
      <attributes>
        <staves>1</staves>
        <clef><sign>percussion</sign><line>2</line></clef>
      </attributes>
    </measure>
  </part>
</score-partwise>
""".strip()
        )

        result = PartIdentifier.identify(tree)

        assert result.parts_map == {"P1": "guitar", "P2": "bass", "P3": "drums"}
        guitar_info = next(part for part in result.parts if part.part_id == "P1")
        assert guitar_info.tab_staff_id == "2"
        assert result.warnings == []

    def test_identify_marks_unknown_part_as_other_and_records_warning(self) -> None:
        from pipeline.transform.part_identifier import PartIdentifier

        tree = _parse_xml(
            """
<score-partwise version="4.0">
  <part-list>
    <score-part id="P9">
      <part-name>Strings</part-name>
      <score-instrument id="P9-I1"><instrument-name>Strings</instrument-name></score-instrument>
    </score-part>
  </part-list>
  <part id="P9"><measure number="1" /></part>
</score-partwise>
""".strip()
        )

        result = PartIdentifier.identify(tree)

        assert result.parts_map == {"P9": "other"}
        assert result.warnings == ["Strings"]

    def test_identify_with_default_role_guitar_overrides_fallback(self) -> None:
        """default_role='guitar' を渡すと未識別パートが guitar になる。"""
        from pipeline.transform.part_identifier import PartIdentifier

        tree = _parse_xml(
            """
<score-partwise version="4.0">
  <part-list>
    <score-part id="P1">
      <part-name>Voice</part-name>
      <score-instrument id="P1-I1"><instrument-name>Voice Oohs</instrument-name></score-instrument>
    </score-part>
    <score-part id="P2">
      <part-name>Voice</part-name>
      <score-instrument id="P2-I1"><instrument-name>Voice Oohs</instrument-name></score-instrument>
    </score-part>
  </part-list>
  <part id="P1"><measure number="1" /></part>
  <part id="P2"><measure number="1" /></part>
</score-partwise>
""".strip()
        )

        result = PartIdentifier.identify(tree, default_role="guitar")

        assert result.parts_map == {"P1": "guitar", "P2": "guitar"}

    def test_identify_default_role_does_not_override_explicit_drums(self) -> None:
        """default_role='guitar' でも明示的ドラムは drums として識別される。"""
        from pipeline.transform.part_identifier import PartIdentifier

        tree = _parse_xml(
            """
<score-partwise version="4.0">
  <part-list>
    <score-part id="P1">
      <part-name>Drums</part-name>
      <score-instrument id="P1-I1"><instrument-name>Drum Kit</instrument-name></score-instrument>
    </score-part>
    <score-part id="P2">
      <part-name>Voice</part-name>
      <score-instrument id="P2-I1"><instrument-name>Voice Oohs</instrument-name></score-instrument>
    </score-part>
  </part-list>
  <part id="P1"><measure number="1"><attributes><clef><sign>percussion</sign></clef></attributes></measure></part>
  <part id="P2"><measure number="1" /></part>
</score-partwise>
""".strip()
        )

        result = PartIdentifier.identify(tree, default_role="guitar")

        assert result.parts_map["P1"] == "drums"
        assert result.parts_map["P2"] == "guitar"

    def test_annotate_writes_transform_role_attribute(self) -> None:
        from pipeline.transform.part_identifier import PartIdentifier, PartIdentifierResult, PartInfo

        tree = _parse_xml(
            """
<score-partwise version="4.0">
  <part-list>
    <score-part id="P1"><part-name>Lead Guitar</part-name></score-part>
  </part-list>
  <part id="P1"><measure number="1" /></part>
</score-partwise>
""".strip()
        )
        result = PartIdentifierResult(
            parts=[PartInfo(part_id="P1", part_name="Lead Guitar", role="guitar", tab_staff_id="2")],
            parts_map={"P1": "guitar"},
            warnings=[],
        )

        annotated = PartIdentifier.annotate(tree, result)

        role = annotated.xpath("string(//*[local-name()='part'][1]/@*[local-name()='role'])")
        assert role == "guitar"
