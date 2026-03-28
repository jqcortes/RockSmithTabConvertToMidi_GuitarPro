"""tests for repeat/navigation expansion in Render domain."""

from __future__ import annotations

from lxml import etree


def _parse_part(xml: str) -> etree._Element:
    root = etree.fromstring(xml.encode("utf-8"))
    return root.xpath("//*[local-name()='part']")[0]


class TestRepeatExpander:
    def test_expand_part_measures_handles_repeat_with_endings(self) -> None:
        from pipeline.render.repeat_expander import RepeatExpander

        part = _parse_part(
            """
<score-partwise version="4.0">
  <part-list><score-part id="P1"><part-name>Guitar</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <barline location="left"><repeat direction="forward"/></barline>
    </measure>
    <measure number="2">
      <barline location="right">
        <ending number="1" type="start"/>
        <repeat direction="backward"/>
      </barline>
    </measure>
    <measure number="3">
      <barline location="left"><ending number="2" type="start"/></barline>
    </measure>
  </part>
</score-partwise>
""".strip()
        )

        result = RepeatExpander.expand_part_measures(part)
        numbers = [int(measure.get("number", "0")) for measure in result.measures]

        assert numbers == [1, 2, 1, 3]
        assert result.warnings == []

    def test_expand_part_measures_handles_dacapo_and_fine(self) -> None:
        from pipeline.render.repeat_expander import RepeatExpander

        part = _parse_part(
            """
<score-partwise version="4.0">
  <part-list><score-part id="P1"><part-name>Guitar</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1"/>
    <measure number="2"><direction><sound dacapo="yes"/></direction></measure>
    <measure number="3"><direction><sound fine="yes"/></direction></measure>
  </part>
</score-partwise>
""".strip()
        )

        result = RepeatExpander.expand_part_measures(part)
        numbers = [int(measure.get("number", "0")) for measure in result.measures]

        assert numbers == [1, 2, 1, 2, 3]

    def test_expand_part_measures_handles_dalsegno_tocoda_and_coda(self) -> None:
        from pipeline.render.repeat_expander import RepeatExpander

        part = _parse_part(
            """
<score-partwise version="4.0">
  <part-list><score-part id="P1"><part-name>Guitar</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1"><direction><direction-type><segno/></direction-type></direction></measure>
    <measure number="2"/>
    <measure number="3"><direction><sound dalsegno="yes"/></direction></measure>
    <measure number="4"><direction><sound tocoda="yes"/></direction></measure>
    <measure number="5"><direction><direction-type><coda/></direction-type></direction></measure>
  </part>
</score-partwise>
""".strip()
        )

        result = RepeatExpander.expand_part_measures(part)
        numbers = [int(measure.get("number", "0")) for measure in result.measures]

        assert numbers == [1, 2, 3, 1, 2, 3, 4, 5]
        assert result.warnings == []

    def test_expand_part_measures_emits_warning_for_tocoda_without_coda(self) -> None:
        from pipeline.render.repeat_expander import RepeatExpander

        part = _parse_part(
            """
<score-partwise version="4.0">
  <part-list><score-part id="P1"><part-name>Guitar</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1"><direction><sound dalsegno="yes"/></direction></measure>
    <measure number="2"><direction><sound tocoda="yes"/></direction></measure>
  </part>
</score-partwise>
""".strip()
        )

        result = RepeatExpander.expand_part_measures(part)

        assert any("tocoda" in warning for warning in result.warnings)

    def test_expand_part_measures_with_context_bridges_cross_page_repeat(self) -> None:
        from pipeline.render.repeat_expander import RepeatExpander, RepeatExpansionContext

        # Page 1 starts a repeat but does not close it.
        part_page1 = _parse_part(
            """
<score-partwise version="4.0">
  <part-list><score-part id="P1"><part-name>Guitar</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1"><barline location="left"><repeat direction="forward"/></barline></measure>
    <measure number="2"/>
  </part>
</score-partwise>
""".strip()
        )

        # Page 2 closes the repeat with a backward marker.
        part_page2 = _parse_part(
            """
<score-partwise version="4.0">
  <part-list><score-part id="P1"><part-name>Guitar</part-name></score-part></part-list>
  <part id="P1">
    <measure number="3"><barline location="right"><repeat direction="backward"/></barline></measure>
  </part>
</score-partwise>
""".strip()
        )

        context = RepeatExpansionContext.empty()
        page1 = RepeatExpander.expand_part_measures_with_context(part_page1, part_id="P1", context=context)
        page2 = RepeatExpander.expand_part_measures_with_context(part_page2, part_id="P1", context=context)

        assert [int(m.get("number", "0")) for m in page1.measures] == [1, 2]
        # Page 2 contributes current page once, then the bridged repeat segment (1,2,3).
        assert [int(m.get("number", "0")) for m in page2.measures] == [3, 1, 2, 3]
        assert any("cross-page repeat bridged" in warning for warning in page2.warnings)
