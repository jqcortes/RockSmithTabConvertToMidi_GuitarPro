"""tests for ConfidenceFilter."""

from __future__ import annotations

from lxml import etree


def _parse_xml(content: str) -> etree._ElementTree:
    return etree.ElementTree(etree.fromstring(content.encode("utf-8")))


class TestConfidenceFilter:
    def test_filter_removes_notes_below_threshold_and_records_details(self) -> None:
        from pipeline.transform.confidence_filter import ConfidenceFilter

        tree = _parse_xml(
            """
<score-partwise version="4.0">
  <part-list>
    <score-part id="P1"><part-name>Lead Guitar</part-name></score-part>
  </part-list>
  <part id="P1" transform:role="guitar" xmlns:transform="https://band-score-to-midi/transform">
    <measure number="1">
      <note confidence="0.4">
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>1</duration>
      </note>
      <note confidence="0.9">
        <pitch><step>D</step><octave>4</octave></pitch>
        <duration>1</duration>
      </note>
    </measure>
  </part>
</score-partwise>
""".strip()
        )

        result = ConfidenceFilter.filter(tree)

        remaining = result.tree.xpath("count(//*[local-name()='note'])")
        assert remaining == 1.0
        assert result.total == 2
        assert len(result.removed) == 1
        assert result.removed[0].measure == "1"
        assert result.removed[0].part_id == "P1"
        assert result.removed[0].pitch == "C4"
        assert result.removed[0].confidence == 0.4
        assert result.filter_rate == 0.5

    def test_filter_keeps_notes_without_confidence_attribute(self) -> None:
        from pipeline.transform.confidence_filter import ConfidenceFilter

        tree = _parse_xml(
            """
<score-partwise version="4.0">
  <part-list>
    <score-part id="P1"><part-name>Lead Guitar</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>1</duration>
      </note>
    </measure>
  </part>
</score-partwise>
""".strip()
        )

        result = ConfidenceFilter.filter(tree)

        remaining = result.tree.xpath("count(//*[local-name()='note'])")
        assert remaining == 1.0
        assert result.total == 1
        assert result.removed == []
        assert result.filter_rate == 0.0