"""tests for GuitarFixer."""

from __future__ import annotations

from pathlib import Path

from lxml import etree


def _parse_xml(content: str) -> etree._ElementTree:
    return etree.ElementTree(etree.fromstring(content.encode("utf-8")))


class TestGuitarFixerApply:
    def test_apply_skips_when_no_tab_staff_present(self) -> None:
        from pipeline.transform.guitar_fixer import GuitarFixer

        tree = _parse_xml(
            """
<score-partwise version="4.0">
  <part-list>
    <score-part id="P1"><part-name>Guitar</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <staves>1</staves>
      </attributes>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>1</duration>
        <voice>1</voice>
        <type>quarter</type>
        <staff>1</staff>
      </note>
    </measure>
  </part>
</score-partwise>
""".strip()
        )

        result = GuitarFixer.apply(tree)

        pitch_text = result.tree.xpath("string(//*[local-name()='note'][1]/*[local-name()='pitch']/*[local-name()='step'])")
        assert result.applied == 0
        assert result.skipped == 0
        assert pitch_text == "C"

    def test_apply_overwrites_pitch_from_tab_staff(self) -> None:
        from pipeline.transform.guitar_fixer import GuitarFixer

        tree = _parse_xml(
            """
<score-partwise version="4.0">
  <part-list>
    <score-part id="P1"><part-name>Lead Guitar</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <staves>2</staves>
        <staff-details number="2"><staff-lines>6</staff-lines></staff-details>
        <clef number="2"><sign>TAB</sign><line>5</line></clef>
      </attributes>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>2</duration>
        <voice>1</voice>
        <type>half</type>
        <staff>1</staff>
      </note>
      <note>
        <duration>2</duration>
        <voice>1</voice>
        <type>half</type>
        <staff>2</staff>
        <notations>
          <technical>
            <string>1</string>
            <fret>3</fret>
          </technical>
        </notations>
      </note>
    </measure>
  </part>
</score-partwise>
""".strip()
        )

        result = GuitarFixer.apply(tree)

        step = result.tree.xpath("string(//*[local-name()='note'][*[local-name()='staff']='1']/*[local-name()='pitch']/*[local-name()='step'])")
        octave = result.tree.xpath("string(//*[local-name()='note'][*[local-name()='staff']='1']/*[local-name()='pitch']/*[local-name()='octave'])")
        assert result.applied == 1
        assert result.skipped == 0
        assert step == "G"
        assert octave == "4"

    def test_apply_preserves_bend_and_counts_skipped_for_invalid_tab_data(self) -> None:
        from pipeline.transform.guitar_fixer import GuitarFixer

        tree = _parse_xml(
            """
<score-partwise version="4.0">
  <part-list>
    <score-part id="P1"><part-name>Lead Guitar</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <staves>2</staves>
        <staff-details number="2"><staff-lines>6</staff-lines></staff-details>
      </attributes>
      <note>
        <pitch><step>D</step><octave>4</octave></pitch>
        <duration>1</duration>
        <voice>1</voice>
        <type>quarter</type>
        <staff>1</staff>
      </note>
      <note>
        <duration>1</duration>
        <voice>1</voice>
        <type>quarter</type>
        <staff>2</staff>
        <notations>
          <technical>
            <string>bad</string>
            <fret>7</fret>
            <bend>
              <bend-alter>1</bend-alter>
            </bend>
          </technical>
        </notations>
      </note>
    </measure>
  </part>
</score-partwise>
""".strip()
        )

        result = GuitarFixer.apply(tree)

        bend = result.tree.xpath("string(//*[local-name()='bend']/*[local-name()='bend-alter'])")
        step = result.tree.xpath("string(//*[local-name()='note'][*[local-name()='staff']='1']/*[local-name()='pitch']/*[local-name()='step'])")
        assert result.applied == 0
        assert result.skipped == 1
        assert bend == "1"
        assert step == "D"


class TestGuitarFixerHelpers:
    def test_fret_to_pitch_uses_standard_and_custom_tuning(self) -> None:
        from pipeline.transform.guitar_fixer import GuitarFixer

        assert GuitarFixer.fret_to_pitch(1, 3, [40, 45, 50, 55, 59, 64]) == 67
        assert GuitarFixer.fret_to_pitch(6, 0, [38, 45, 50, 55, 59, 64]) == 38

    def test_load_tuning_reads_yaml_and_falls_back_to_standard(self, tmp_path: Path) -> None:
        from pipeline.transform.guitar_fixer import GuitarFixer, STANDARD_TUNING

        config_path = tmp_path / "instrument_map.yaml"
        config_path.write_text(
            """
tunings:
  standard: [40, 45, 50, 55, 59, 64]
  drop_d: [38, 45, 50, 55, 59, 64]
""".strip(),
            encoding="utf-8",
        )

        assert GuitarFixer.load_tuning("drop_d", config_path) == [38, 45, 50, 55, 59, 64]
        assert GuitarFixer.load_tuning("missing", config_path) == STANDARD_TUNING
        assert GuitarFixer.load_tuning("drop_d", tmp_path / "missing.yaml") == STANDARD_TUNING